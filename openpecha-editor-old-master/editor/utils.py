import base64
import shutil
from pathlib import Path

import requests
from antx import transfer
from antx.ann_patterns import HFML_ANN_PATTERN
from flask import current_app
from github3 import GitHub
from github3.apps import create_jwt_headers
from openpecha.formatters import HFMLFormatter
from openpecha.formatters.layers import AnnType
from openpecha.github_utils import create_release
from openpecha.serializers import EpubSerializer, HFMLSerializer


def get_opf_layers_and_formats(pecha_id):
    meta_url = f"https://raw.githubusercontent.com/OpenPecha/{pecha_id}/master/{pecha_id}.opf/meta.yml"
    content = requests.get(meta_url).content.decode()
    layer_names = []
    formats = [".epub"]
    for layer_name in content.split("layers:")[-1].split("-"):
        cleaned_layer_name = layer_name.strip()
        if not cleaned_layer_name:
            continue
        layer_names.append(cleaned_layer_name)
    return layer_names, formats


def get_installation_id(owner, repo):
    "https://developer.github.com/v3/apps/#find-repository-installation"
    url = f"https://api.github.com/repos/{owner}/{repo}/installation"
    headers = create_jwt_headers(
        current_app.config["GITHUBAPP_KEY"], current_app.config["GITHUBAPP_ID"]
    )

    response = requests.get(url=url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Status code : {response.status_code}, {response.json()}")
    return response.json()["id"]


def get_installation_access_token(installation_id):
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = create_jwt_headers(
        current_app.config["GITHUBAPP_KEY"], current_app.config["GITHUBAPP_ID"]
    )

    response = requests.post(url=url, headers=headers)
    if response.status_code != 201:
        raise Exception(f"Status code : {response.status_code}, {response.json()}")
    return response.json()["token"]


def create_issue(pecha_id, title, body=None, labels=[]):
    # Authenticating bot as an installation
    installation_id = get_installation_id(
        owner=current_app.config["GITHUBREPO_OWNER"], repo=pecha_id
    )
    installation_access_token = get_installation_access_token(installation_id)
    client = GitHub(token=installation_access_token)

    issue = client.create_issue(
        current_app.config["GITHUBREPO_OWNER"],
        pecha_id,
        title,
        body=body,
        labels=labels,
    )

    return issue


def create_export_issue(pecha_id, layers="", format_=".epub"):
    issue_title = "Export"
    issue_body = f"{','.join(layers)}\n{format_}"
    issue = create_issue(pecha_id, issue_title, body=issue_body, labels=["export"])
    return issue


def download_file(url, out_fn):
    r = requests.get(url, stream=True)
    if r.status_code == 200:
        out_fn.parent.mkdir(exist_ok=True, parents=True)
        out_fn.write_bytes(r.content)


class PechaExporter:
    """This class exports pecha into specified format with selected layers."""

    def __init__(self, pecha_id, oauth_token, layers="publication", format_=".epub"):
        self.oauth_token = oauth_token
        self.headers = {"Authorization": f"token {self.oauth_token}"}

        self.pecha_id = pecha_id
        self.base_layer_name = "BaseText"
        default_layers = [
            self.base_layer_name,
            AnnType.book_title,
            AnnType.poti_title,
            AnnType.author,
            AnnType.chapter,
        ]
        self.layers = default_layers + layers
        self.format_ = format_

        self._prepare_paths()

        self.parser = HFMLFormatter(output_path=self.base_path)
        self.serializer = None

        self.content_url_template = (
            "https://api.github.com/repos/OpenPecha/{}/contents/{}?ref={}"
        )

    def _prepare_paths(self):
        self.base_path = Path("/tmp") / "openpecha"
        self.pecha_path = self.base_path / self.pecha_id
        if self.pecha_path.is_dir():
            self.clean()
        self.pecha_path.mkdir(exist_ok=True, parents=True)

        self.layers_path = self.pecha_path / "layers"
        self.layers_path.mkdir(exist_ok=True, parents=True)
        self.merged_layers_path = self.pecha_path / "merged_layers"
        self.merged_layers_path.mkdir(exist_ok=True, parents=True)
        self.exports_path = self.pecha_path / "exports"
        self.exports_path.mkdir(exist_ok=True, parents=True)

    @staticmethod
    def _get_serializer(format_, **kwargs):
        if format_ == ".epub":
            return EpubSerializer(**kwargs)
        else:
            return HFMLSerializer(**kwargs)

    def get_response_json(self, url, headers={}):
        r = requests.get(url, headers=self.headers)
        if r.status_code != 200:
            return []
        return r.json()

    def _get_layers_git_urls(self):
        for layer in self.layers:
            files = self.get_response_json(
                self.content_url_template.format(self.pecha_id, "", layer)
            )
            for file in files:
                yield layer, file["name"], file["git_url"]

    def _get_base64_content(self, git_url):
        data = self.get_response_json(git_url)
        return base64.b64decode(data["content"]).decode("utf-8")

    def download_layers(self):
        """Download layers."""
        for layer, fn, git_url in self._get_layers_git_urls():
            layer_path = self.layers_path / layer
            layer_path.mkdir(exist_ok=True)
            out_fn = layer_path / fn
            content = self._get_base64_content(git_url)
            out_fn.write_text(content)

    def _download_github_dir(self, items):
        for item in items:
            if item["type"] == "file":
                out_fn = self.pecha_path / item["path"]
                download_file(item["download_url"], out_fn)
            else:
                dir_url = item["url"]
                items = self.get_response_json(dir_url)
                self._download_github_dir(items)

    def download_assets(self):
        """Download all assets of pecha."""
        asset_path = f"{self.pecha_id}.opf/asset"
        asset_url = self.content_url_template.format(
            self.pecha_id, asset_path, "master"
        )
        items = self.get_response_json(asset_url)
        self._download_github_dir(items)

    def download_metadata(self):
        meta_path = f"{self.pecha_id}.opf/meta.yml"
        meta_url = self.content_url_template.format(self.pecha_id, meta_path, "master")
        meta = self.get_response_json(meta_url)
        out_fn = self.pecha_path / meta["path"]
        download_file(meta["download_url"], out_fn)

    def _merge_layers_for_vol(self, base_vol_fn):
        """Merge all the layers of a volume."""
        base_layer = base_vol_fn.read_text()
        vol_fn = base_vol_fn.name
        for ann_layer_name in self.layers[1:]:
            ann_layer_vol_fn = self.layers_path / ann_layer_name / vol_fn
            if not ann_layer_vol_fn.is_file():
                continue
            ann_layer = ann_layer_vol_fn.read_text()
            base_layer = transfer(ann_layer, HFML_ANN_PATTERN, base_layer, "txt")

        merged_layers_fn = self.merged_layers_path / vol_fn
        merged_layers_fn.write_text(base_layer.replace(">>", ">"))

    def merge_layers(self):
        for base_vol_fn in (self.layers_path / self.base_layer_name).iterdir():
            self._merge_layers_for_vol(base_vol_fn)

    def parse(self):
        """Parser layers into opf."""
        self.parser.create_opf(self.merged_layers_path, id_=self.pecha_id)

    def serialize(self):
        """Serialize the opf into given format."""
        serializer = self._get_serializer(
            self.format_, opf_path=self.parser.dirs["opf_path"]
        )
        serializer.apply_layers()
        exported_fn = serializer.serialize(output_path=self.exports_path)
        return exported_fn

    def create_pre_release(self):
        """Create pre-release and return the asset link."""
        download_url = create_release(
            self.pecha_id,
            prerelease=True,
            assets_path=list(self.exports_path.iterdir()),
            token=self.oauth_token,
        )
        return download_url

    def clean(self):
        """Remove downloaded layers, hfml file, opf and exported file."""
        shutil.rmtree(str(self.pecha_path))

    def export(self):
        self.download_layers()
        self.merge_layers()
        self.parse()
        self.download_assets()
        self.download_metadata()
        self.serialize()
        asset_download_url = self.create_pre_release()
        return asset_download_url


def create_export(pecha_id, layers, format_, token):
    exporter = PechaExporter(pecha_id, token, layers, format_)
    asset_download_url = exporter.export()
    return asset_download_url
