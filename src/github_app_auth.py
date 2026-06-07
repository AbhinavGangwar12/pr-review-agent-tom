import os
from github import Auth, Github, GithubIntegration


def get_github_client(repo_full_name: str) -> Github:
    """
    Returns a Github client authenticated as the app installation
    for the given repo. Works on any repo where the app is installed.
    """
    app_id      = os.getenv("GITHUB_APP_ID")
    private_key = os.getenv("GITHUB_APP_PRIVATE_KEY").replace("\\n", "\n")

    integration  = GithubIntegration(auth=Auth.AppAuth(app_id, private_key))
    owner, repo  = repo_full_name.split("/")
    installation = integration.get_repo_installation(owner, repo)
    access_token = integration.get_access_token(installation.id)

    return Github(auth=Auth.Token(access_token.token))