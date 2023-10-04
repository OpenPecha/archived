import time

import requests
from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from editor.extensions import github_oauth
from editor.user.models import RoleType, User
from editor.utils import (
    create_export,
    create_export_issue,
    create_issue,
    get_opf_layers_and_formats,
)

blueprint = Blueprint("main", __name__, url_prefix="/", static_folder="../static")


@blueprint.route("/")
def index():
    return render_template("index.html")


@blueprint.route("/<pecha_id>")
def editor(pecha_id):
    # login or register to github account
    if "user_id" not in session:
        if "user_id" in session:
            return redirect(url_for("main.editor", pecha_id=pecha_id))
        session["next_url"] = url_for("main.editor", pecha_id=pecha_id)
        return render_template("login.html")

    # Register user to text repo if not
    user = User.query.get(session["user_id"])
    if not user.pecha_id:
        return render_template("register.html", pecha_id=pecha_id)

    is_owner = False
    if user.role == RoleType.owner:
        is_owner = True
    layers, formats = get_opf_layers_and_formats(pecha_id)
    return render_template(
        "main.html",
        pecha_id=pecha_id,
        layers=layers,
        formats=formats,
        is_owner=is_owner,
    )


@blueprint.route("/export", methods=["POST"])
def export():
    # Get layers and format
    pecha_id = request.args.get("pecha_id")
    layers = request.form.getlist("layers")
    format_ = request.form.getlist("format")

    # Create github issue
    asset_download_url = create_export(
        pecha_id, layers, format_[0], session.get("user_access_token")
    )

    if asset_download_url:
        return render_template("download_page.html", download_url=asset_download_url)
        # flash( #     f"{pecha_id} is being exported. Please go to Download section to download the file", #     "info", # )
    else:
        flash(f"{pecha_id} cloud not be exported. Please try again later", "danger")
        return redirect(url_for("main.index", pecha_id=pecha_id))


@blueprint.route("/publish")
def publish():
    pecha_id = request.args.get("pecha_id")

    # Login with Github
    if session.get("user_id", None) is None:
        session["next_url"] = url_for("main.publish", pecha_id=pecha_id)
        return github_oauth.authorize()

    user = User.query.get(session["user_id"])
    if user.role == RoleType.owner:
        issue_title = "Update OPF"
        issue_body = "create publish"
        issue = create_issue(pecha_id, issue_title, body=issue_body, labels=["publish"])

        if issue:
            flash(
                f"{pecha_id} is being updated. This may take a few minutes", "success"
            )
        else:
            flash(
                f"{pecha_id} cloud not be updated at the moment. Please try again later",
                "danger",
            )
    else:
        flash("Only owner can update the pecha", "danger")

    return redirect(url_for("main.index", pecha_id=pecha_id))


@blueprint.route("/download/<org>/<pecha_export_fn>")
def download(org, pecha_export_fn):
    download_api_url = url_for(
        "main.download_api", org=org, pecha_export_fn=pecha_export_fn, _external=True
    )
    print(download_api_url)
    r = requests.get(download_api_url)
    return redirect(r.json()["download_url"])


# ~~~~~~ API ~~~~~~~


@blueprint.route("/api/download/<org>/<pecha_export_fn>")
def download_api(org, pecha_export_fn):
    pecha_id, format_ = pecha_export_fn.split(".")
    json_response = {
        "pecha_id": pecha_id,
        "export_format": format_,
        "download_url": f"https://github.com/{org}/{pecha_id}/releases/latest/download/{pecha_export_fn}",
    }
    is_export_issue_created = False
    while True:
        r = requests.get(json_response["download_url"])
        if r.status_code == 200:
            return jsonify(json_response)
        else:
            if not is_export_issue_created:
                create_export_issue(pecha_id, format_=f".{format_}")
                is_export_issue_created = True
            time.sleep(5)
