import { Octokit } from "https://cdn.skypack.dev/@octokit/core";

async function getOAuthToken() {
    const response = await fetch('/users/api/auth');
    const data = await response.json();
    return data['token'];
}

export async function getGHClient() {
    const oauth_token = await getOAuthToken();
    const octokit = new Octokit({ auth: oauth_token });
    return octokit;
}
