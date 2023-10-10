import logging
import urllib.request
from pathlib import Path
from urllib.error import HTTPError

import requests
from git import Repo

from openpecha.core.pecha import OpenPechaBareGitRepo

ENV = {"GIT_TERMINAL_PROMPT": "0"}

class OpenpechaCachedGit:
    """
    The OpenpechaGit class is here to help manage and pull all the Openpecha objects and store them on a temporary local
    repository
    It is initiated with
    - The Openpecha _pecha_id
    - The local dir (by default stored in ~/.openpecha/data)
    - The remote git of Openpecha
    - If we want the bare repo or a working tree on the local branch (by default the bare repo to save some space)
    """

    def __init__(
        self,
        pecha_id,
        github_org="Openpecha-data",
        github_token=None,
        cache_dir_path=Path.home() / ".cache" / "openpecha",
        bare=True
    ):
        self._pecha_id = pecha_id
        self.cache_dir_base = cache_dir_path
        cache_dir_parent = cache_dir_path / pecha_id[-2:]
        cache_dir_parent.mkdir(parents=True, exist_ok=True)
        self.cache_dir = cache_dir_parent / (pecha_id+".git")
        self.openpecha_dstgit = f"https://{github_org}:{github_token}@github.com/{github_org}/{self._pecha_id}.git"
        self.bare = bare
        self.repo = None
        self.synced = False

    def get_repo(self, dst_sync=False):
        """
        gets the repo, sync with dst (Github) if parameter is true, otherwise just return the local repo
        """
        if self.repo is not None:
            if dst_sync and not self.synced:
                self.repo.git.fetch()
                self.synced = True
            return self.repo
        if not self.in_cache():
            self.clone()
            return self.repo
        logging.info(f"{self._pecha_id} in git cache in {str(self.cache_dir)}")
        self.repo = Repo(str(self.cache_dir))
        if dst_sync and not self.synced:
            self.repo.git.fetch(kill_after_timeout=20)
            self.synced = True
        return self.repo

    def clone(self):
        """
        Given a _pecha_id, clones the repo from openpecha to self.cache_dir
        """
        if self.in_cache():
            return
        logging.info(f"cloning {self._pecha_id} in {str(self.cache_dir)}")
        self.repo = Repo.clone_from(
            self.openpecha_dstgit,
            str(self.cache_dir),
            env=ENV,
            bare=self.bare,
            kill_after_timeout=20
        )
        self.synced = True

    def in_cache(self):
        """
        Check if self._pecha_id has already been cloned by looking if there is
        a folder with the self._pecha_id name in the local directory
        """
        return self.cache_dir.is_dir()

    def get_local_latest_commit(self, dst_sync=False, branchname=None):
        """
        get the commit to sync to BUDA: the latest tag, or the latest commit of the master branch
        """
        repo = self.get_repo(dst_sync)
        tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)
        if tags:
            return tags[-1].commit.hexsha
        try:
            if branchname is None:
                if "main" in repo.branches:
                    branchname = "main"
                elif "master" in repo.branches:
                    branchname = "master"
                else:
                    logging.error("cannot guess branch name for %s", self._pecha_id)
                    return None
            return repo.commit(branchname).hexsha
        except Exception:
            logging.exception("cannot find branch %s for %s", branchname, self._pecha_id)
            return None

    def get_openpecha(self, rev=None):
        if rev is None:
            rev = self.get_local_latest_commit()
        if rev is None:
            return None
        if not self.bare:
            print("TODO: implement non-bare repositories!!!")
            return None
        openpecha = OpenPechaBareGitRepo(self._pecha_id, repo=self.get_repo(), revision=rev)
        return openpecha

    def release(self):
        if self.repo:
            # some kind of black magic, not sure it works
            self.repo.git.clear_cache()