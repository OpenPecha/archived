from flask import Blueprint
from flask_githubapp import GitHubApp

blueprint = Blueprint("bot", __name__, url_prefix="/users", static_folder="../static")

# github_app = GitHubApp(Blueprint)


# @github_app.on("issues.opened")
# def cruel_closer():
#     owner = github_app.payload["repository"]["owner"]["login"]
#     repo = github_app.payload["repository"]["name"]
#     num = github_app.payload["issue"]["number"]
#     issue = github_app.installation_client.issue(owner, repo, num)
#     issue.create_comment("Operation is being performed")
#     issue.close()
