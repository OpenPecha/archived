from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from editor.extensions import github_oauth
from editor.pecha.form import PechaSecretKeyForm
from editor.pecha.models import Pecha

from .models import RoleType, User

blueprint = Blueprint("user", __name__, url_prefix="/users", static_folder="../static")


@github_oauth.access_token_getter
def token_getter():
    return session.get("user_access_token", None)


@blueprint.route("/github-callback")
@github_oauth.authorized_handler
def authorized(access_token):
    next_url = session.get("next_url")
    if access_token is None:
        flash("Authorization failed.", category="error")
        return redirect(next_url)
    session["user_access_token"] = access_token
    github_user = github_oauth.get("/user")
    user = User.query.filter_by(username=github_user["login"]).first()

    # add user to database
    if user is None:
        user = User.create(username=github_user["login"])
        # add admin user
        if not user.role and user.username in current_app.config["OP_ADMIN_USERS"]:
            user.update(role=RoleType.admin)

    session["user_id"] = user.id
    return redirect(next_url)


@blueprint.route("/login")
def login():
    return github_oauth.authorize()


@blueprint.route("/logout")
def logout():
    pecha_id = request.args.get("pecha_id")
    branch = request.args.get("branch")
    session.pop("user_id", None)
    return redirect(url_for("main.index", pecha_id=pecha_id, branch=branch))


@blueprint.route("/validate-secret", methods=["GET", "POST"])
def validate_secret_key():
    pecha_id = request.args.get("pecha_id")
    form = PechaSecretKeyForm()
    if request.method != "POST":
        context = {
            "title": "Secret Key",
            "form": form,
            "pecha_id": pecha_id,
            "is_owner": False,
        }
        return render_template("secret_key_form.html", **context)

    if form.validate_on_submit():
        secret_key = form.secret_key.data
        if len(secret_key) == 32:
            pecha = Pecha.query.filter_by(secret_key=secret_key).first()
            if pecha:
                return redirect(
                    url_for("user.register_user", pecha_id=pecha.id, is_owner=True)
                )
        flash("Invalid Pecha Secret Key!", "danger")
        return redirect(url_for("main.index", pecha_id=pecha_id))


@blueprint.route("/register-user", methods=["GET", "POST"])
def register_user():
    pecha_id = request.args.get("pecha_id")
    is_owner = request.args.get("is_owner")

    # Update pecha-id and role of the user
    user = User.query.get(session["user_id"])
    if is_owner == "True":
        user.update(role=RoleType.owner)
    else:
        user.update(role=RoleType.contributor)
    user.update(pecha_id=pecha_id)
    send_invitation(user, pecha_id)

    return redirect(url_for("main.editor", pecha_id=pecha_id))


def send_invitation(user, pecha_id):
    add_collaborator_url = f"https://api.github.com/repos/OpenPecha/{pecha_id}/collaborators/{user.username}"
    headers = {"Authorization": f"token {current_app.config['GITHUB_TOKEN']}"}
    res = github_oauth.session.request("PUT", add_collaborator_url, headers=headers)
    if res.status_code == 201:
        flash(
            f"Please check your Github linked Email to complete the Registration to {pecha_id}",
            "info",
        )
    elif res.status_code == 204:
        flash(f"User already registered to {pecha_id}", "info")
    else:
        flash("Registration failed. Please try again later", "danger")


@blueprint.route("/admin")
def admin_dashboard():
    if session.get("user_id", None) is None:
        session["next_url"] = url_for("user.admin_dashboard")
        return render_template("login.html")

    user = User.query.get(session["user_id"])
    if user.username not in current_app.config["OP_ADMIN_USERS"]:
        return "You don't have access to this page"

    pechas = Pecha.query.all()
    users = User.query.all()
    return render_template(
        "admin_page.html", title="Admin Page", pechas=pechas, users=users
    )


# ~~~~~~ API ~~~~~~~


@blueprint.route("/api/auth")
def auth():
    if "user_id" in session:
        user = User.query.get(session["user_id"])
        if user:
            result = {"status": 200, "token": session["user_access_token"]}
        else:
            result = {"status": 404, "message": "User not registered."}
    else:
        result = {
            "status": 404,
            "message": "User not logged in. Please login to openpecha editor",
        }
    return jsonify(result)
