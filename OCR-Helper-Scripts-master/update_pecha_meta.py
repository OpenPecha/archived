import shutil
import requests
import subprocess
from git import Repo
from github import Github
from pathlib import Path
from rdflib import Graph
from rdflib.namespace import RDF, RDFS, SKOS, OWL, Namespace, NamespaceManager, XSD
from openpecha.utils import load_yaml, dump_yaml

config = {
    "OP_ORG": "https://github.com/Openpecha-Data"
}

BDR = Namespace("http://purl.bdrc.io/resource/")
BDO = Namespace("http://purl.bdrc.io/ontology/core/")

def clean_dir(layers_output_dir):
    if layers_output_dir.is_dir():
            shutil.rmtree(str(layers_output_dir))

def commit(repo, message, not_includes=[], branch="master"):
    has_changed = False

    for fn in repo.untracked_files:
        ignored = False
        for not_include_fn in not_includes:
            if not_include_fn in fn:
                ignored = True
        if ignored:
            continue
        if fn:
            repo.git.add(fn)
        if has_changed is False:
            has_changed = True

    if repo.is_dirty() is True:
        for fn in repo.git.diff(None, name_only=True).split("\n"):
            if fn:
                repo.git.add(fn)
            if has_changed is False:
                has_changed = True
        if has_changed is True:
            if not message:
                message = "Initial commit"
            repo.git.commit("-m", message)
            repo.git.push("origin", branch)        
    
        
def setup_auth(repo, org, token):
    remote_url = repo.remote().url
    old_url = remote_url.split("//")
    authed_remote_url = f"{old_url[0]}//{org}:{token}@{old_url[1]}"
    repo.remote().set_url(authed_remote_url)


def push_changes(pecha_path, commit_msg, token):
    repo = Repo(pecha_path)
    setup_auth(repo, "Openpecha-Data", token)
    commit(repo, commit_msg, not_includes=[],branch="master")

def add_legacy_id(pecha_path, legacy_id):
    meta_path = Path(f"{pecha_path}/{pecha_path.name}.opf/meta.yml")
    meta = load_yaml(meta_path)
    meta['legacy_id'] = legacy_id
    base = meta['source_metadata']['base']
    for _, info in base.items():
        info['legacy_id'] = f"v{info['order']:03}"
    meta['source_metadata']['base']
    dump_yaml(meta, meta_path)

def update_meta(source_metadata, meta_path):
    meta = load_yaml(meta_path)
    meta['source_metadata'] = source_metadata
    dump_yaml(meta, meta_path)

def get_new_base(base_info, base_dic):
    base = {}
    curr = {}
    for _, info in base_dic.items():
        new_base = info['base']
        image_group_id = info['image_group_id']
        curr = {
            'image_group_id': base_info[image_group_id]['image_group_id'],
            'title': base_info[image_group_id]['title'],
            'total_pages':  base_info[image_group_id]['total_pages'],
            'order': base_info[image_group_id]['order'] 
        }
        base[new_base]= curr
        curr ={}
    return base


def get_base_dic(pecha_path):
    curr_info = {}
    base_dic = {}
    layer_paths = Path(f"{pecha_path}/{pecha_path.name}.opf/layers/").iterdir()
    for layer_path in layer_paths:
        pagination = load_yaml(Path(f"{layer_path}/Pagination.yml"))
        for uuid, pg_info in pagination['annotations'].items():
            image_group_id = pg_info['reference'][:-4]
            curr_info[uuid] = {
                'base': layer_path.name,
                'image_group_id': image_group_id
            }
            base_dic.update(curr_info)
            curr_info = {}
            break
    return base_dic

def get_img_grp_id(URI):
    return URI.split("/")[-1]


def get_vol_img_grp_id_list(g, work_id):
    vol_img_grp_ids = []
    volumes = g.objects(BDR[work_id], BDO["instanceHasVolume"])
    for volume in volumes:
        vol_img_grp_id = get_img_grp_id(str(volume))
        vol_img_grp_ids.append(vol_img_grp_id)
    vol_img_grp_ids.sort()
    return vol_img_grp_ids

def parse_base_info(meta_ttl, work_id):
    g = Graph()
    try:
        g.parse(data=meta_ttl, format="ttl")
    except:
        return {}
    vol_img_grp_ids = get_vol_img_grp_id_list(g, work_id)
    vol_info = {}
    for vol_img_grp_id in vol_img_grp_ids:
        title = g.value(BDR[vol_img_grp_id], RDFS.comment)
        if title:
            title = title.value
        else:
            title = ""
        volume_number = int(g.value(BDR[vol_img_grp_id], BDO["volumeNumber"]))
        try:
            total_pages = int(g.value(BDR[vol_img_grp_id], BDO["volumePagesTotal"]))
        except:
            total_pages = 0
        vol_info[vol_img_grp_id] = {
            "image_group_id": vol_img_grp_id,
            "title": title,
            "order": volume_number,
            "total_pages": total_pages,
        }
    return vol_info

def get_meta_ttl(work_id):
    try:
        ttl = requests.get(f"http://purl.bdrc.io/graph/{work_id}.ttl")
        return ttl.text
    except:
        print(' TTL not Found!!!')
        return ""

def get_number_of_base(pecha_path):
    base_paths = list(Path(f"{pecha_path}/{pecha_path.name}.opf/layers").iterdir())
    return len(base_paths)

def check_base_of_meta(pecha_path, old_pecha_id, token):
    meta_path = Path(f"{pecha_path}/{pecha_path.name}.opf/meta.yml")
    meta = load_yaml(meta_path)
    source_metadata = meta['source_metadata']
    base = source_metadata['base']
    work_id = source_metadata['id'][4:]
    number_of_base = get_number_of_base(pecha_path)
    if len(base) != number_of_base:
        meta_ttl = get_meta_ttl(work_id)
        if meta_ttl != None:
            base_info = parse_base_info(meta_ttl, work_id)
            base_dic = get_base_dic(pecha_path)
            new_base = get_new_base(base_info, base_dic)
            del source_metadata['base']
            source_metadata['base'] = new_base
            update_meta(source_metadata, meta_path)
    
def get_branch(repo, branch):
    if branch in repo.heads:
        return branch
    return "main"


def download_pecha(pecha_id, out_path=None, branch="master"):
    pecha_url = f"{config['OP_ORG']}/{pecha_id}.git"
    out_path = Path(out_path)
    out_path.mkdir(exist_ok=True, parents=True)
    pecha_path = out_path / pecha_id
    Repo.clone_from(pecha_url, str(pecha_path))
    repo = Repo(str(pecha_path))
    branch_to_pull = get_branch(repo, branch)
    repo.git.checkout(branch_to_pull)
    print(f"{pecha_id} Downloaded ")
    return pecha_path
        
if __name__ == "__main__":
    token = ""
    commit_msg = "updated base of meta"
    ids = load_yaml(Path(f"./pecha_id_with_legacy_id.yml"))
    output_path = Path(f"./pechas")
    for old_id, new_id in ids.items():
        if len(old_id) < 10:
            pecha_path = download_pecha(new_id, output_path)
            check_base_of_meta(pecha_path, old_id, token)
            add_legacy_id(pecha_path, old_id)
            push_changes(pecha_path, commit_msg, token)
            clean_dir(pecha_path)
            