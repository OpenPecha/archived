import csv
import logging
import re
import os
import yaml
from datetime import datetime
from rdflib import ConjunctiveGraph
from rdflib.namespace import Namespace
from github import Github



BDR = Namespace("http://purl.bdrc.io/resource/")
BDO = Namespace("http://purl.bdrc.io/ontology/core/")
BDA = Namespace("http://purl.bdrc.io/admindata/")
ADM = Namespace("http://purl.bdrc.io/ontology/admin/")
BDG = Namespace("http://purl.bdrc.io/graph/")

logging.basicConfig(filename="opf_meta_update.log", level=logging.INFO, filemode="w")


def update_repo(g, pecha_id, file_path, commit_msg, new_content):
    try:
        repo = g.get_repo(f"Openpecha/{pecha_id}")
    except:
        print(f"{pecha_id} repo not found")
    try:
        contents = repo.get_contents(f"{file_path}", ref="master")
        repo.update_file(contents.path, commit_msg , new_content, contents.sha, branch="master")
    except:
        print('Master branch not found')
        try:
            contents = repo.get_contents(f"{file_path}", ref="main")
            repo.update_file(contents.path, commit_msg , new_content, contents.sha, branch="main")
        except:
            print('Main branch not found')
    


def get_meta_from_opf(g, pecha_id):
    try:
        repo = g.get_repo(f"Openpecha/{pecha_id}")
    except:
        logging.info(f'{pecha_id} Repo Not Found')
        return ''
    try:
        contents = repo.get_contents(f"./{pecha_id}.opf/meta.yml", ref="master")
        return contents.decoded_content.decode()
    except:
        print(f'{pecha_id} master branch Not Found')
        try:
            contents = repo.get_contents(f"./{pecha_id}.opf/meta.yml", ref="main")
            return contents.decoded_content.decode()
        except:
            print(f'{pecha_id} main branch Not Found')
            return ''

    
    

def get_access_flag(work_graph, work_id):
    return str(work_graph.value(BDA[work_id], ADM["access"]))

def is_restricted_in_china(work_graph, work_id):
    is_restricted_flag = False
    is_restricted = str(work_graph.value(BDA[work_id], ADM["restrictedInChina"]))
    if is_restricted == "true":
        is_restricted_flag = True
    return is_restricted_flag

def get_new_meta(meta_data, work_id):
    new_meta = meta_data
    if meta_data:
        meta_data = yaml.safe_load(meta_data)
        work_graph = ConjunctiveGraph()
        work_graph.parse(f'http://purl.bdrc.io/graph/{work_id}.trig', format="trig")
        meta_data['last_modified_at'] = datetime.now()
        meta_data['source_metadata']['access'] = get_access_flag(work_graph, work_id)
        meta_data['source_metadata']['restrictedInChina'] = is_restricted_in_china(work_graph, work_id)
        new_meta = yaml.safe_dump(meta_data, default_flow_style=False, sort_keys=False,  allow_unicode=True)
    return new_meta

def get_pecha_id(pecha):
    pecha_id = re.search("\[.+\]", pecha[0])[0][1:-1]
    return pecha_id

def get_work_id(pecha):
    work_id = ''
    if re.search("bdr:.+", pecha[4]):
        work_id = re.search("bdr:(.+)", pecha[4]).group(1)
    return work_id

def update_opf_meta(g, pecha_id, work_id):
    commit_msg = 'meta updated'
    file_path = f"./{pecha_id}.opf/meta.yml"
    old_meta_data = get_meta_from_opf(g, pecha_id)
    new_meta_data = get_new_meta(old_meta_data, work_id)
    update_repo(g, pecha_id, file_path, commit_msg, new_meta_data)

if __name__ == "__main__":
    token = os.environ['GITHUB_TOKEN']
    g = Github(token)

    with open("catalog.csv", newline="") as csvfile:
        pechas = list(csv.reader(csvfile, delimiter=","))
        for pecha in pechas[754:4376]:
            pecha_id = get_pecha_id(pecha)
            work_id = get_work_id(pecha)
            if work_id:
                update_opf_meta(g, pecha_id, work_id)
                print(f'INFO: {pecha_id} meta updated..')

