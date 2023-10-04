import { getGHClient } from "./github.js";
import { loading } from "./utils.js";

function getFileDOM(file, org, repo, branch) {
    return '<a href="#" class="volume-file"> \
                <span class="volume-filename">' + file['name'] + '</span> \
                <input type="hidden" id="sha" value=' + file['sha'] + '> \
                <input type="hidden" id="path" value=' + file['path'] + '> \
            </a>'
};

function getFiles(content, org, repo, branch) {
    var files = '<ul class="list-group overrides">';
    var file_icon = '<span class="oi oi-file"></span>';
    for (var file of content) {
        files += '<li class="list-group-item">' + file_icon + getFileDOM(file, org, repo, branch) + '</li>';
    };
    files += '</ul>';
    return files
};

export async function listFiles(org, repo, branch) {
    loading();
    const ghClient = await getGHClient();
    const gh_response = await ghClient.request('GET /repos/{owner}/{repo}/contents/{path}', {
        owner: org,
        repo: repo,
        ref: branch
    })
    window.gh_org = org;
    window.gh_repo = repo;
    window.repo_branch = branch;
    $('.repo-files').html(getFiles(gh_response.data, org, repo, branch));
    loading("off")
    $("#files-toggle").trigger("click");
    $(".volume-file").trigger("click");
};
