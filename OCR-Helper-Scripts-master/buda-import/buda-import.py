import os
import shutil
from datetime import datetime
import io
import gzip
import json
import hashlib
import logging
import tqdm

from git import Repo 
from pathlib import Path
import gzip
from cached_git_repo import OpenpechaCachedGit
from parallel_executor import ParallelTaskExecutor
from openpecha.serializers.rdf import BUDARDFSerializer


PULL=False
FORCE_REDERIVE = False
SEND_TO_BUDA = False
TTL_CACHE_FOLDER = Path("./ttl-cache")
CACHE_TTL = True
GIT_CACHE_FOLDER = Path("./git_cache")
GIT_CACHE_BARE = True
GIT_PULL = False
ORG_NAME = "Openpecha-data"
TOKEN = Path('../secret.txt').read_text(encoding='utf-8').splitlines()[0]
STORE_URL = "http://buda1.bdrc.io:13180/fuseki/corerw/data"

filesuffix = datetime.now().strftime("%Y%m%d-%H%M%S")
logging.basicConfig(filename='buda-import-'+filesuffix+'.log', filemode='w', level=logging.INFO)

def send_model_to_store(ttl_str, graph_uri):
    logging.info("sending %s to store", graphuri)
    headers = {"Content-Type": "text/turtle"}
    params = {"graph": graph_uri}
    try:
        r = requests.put(STORE_URL, data=ttl_str, headers=headers, params=params)
        sc = r.status_code
        if (
            sc != requests.codes.ok
            and sc != requests.codes.created
            and sc != requests.codes.accepted
        ):
            logging.error("The request to Fuseki returned code " + str(r.status_code) + " for " + graphuri)
    except:
        logging.exception("The request to Fuseki had an exception for " + graphuri)

def get_graph_ttl_str(pecha_id):
    buda_graph_ttl_str = None
    ttl_file_path = TTL_CACHE_FOLDER / pecha_id[-2:] / ("IE0OP"+pecha_id+".ttl.gz")
    if CACHE_TTL and not FORCE_REDERIVE and ttl_file_path.is_file():
        if not SEND_TO_BUDA:
            # in that case the parent function doesn't need the string anyways so
            # so we don't read it
            return "cached", ""
        with gzip.open(str(ttl_file_path), 'rb') as gzf:
            return "cached", gzf.read()
    cached_op_git = OpenpechaCachedGit(pecha_id, github_org=ORG_NAME, github_token=TOKEN, bare=GIT_CACHE_BARE, cache_dir_path=GIT_CACHE_FOLDER)
    git_rev = cached_op_git.get_local_latest_commit(dst_sync=GIT_PULL)
    op = cached_op_git.get_openpecha(git_rev)
    cached_op_git.release()
    rdf_serializer = BUDARDFSerializer(op)
    rdf_serializer.apply_layers()
    buda_graph_ttl_str = rdf_serializer.get_result().serialize(format="ttl")
    if CACHE_TTL:
        (TTL_CACHE_FOLDER / pecha_id[-2:]).mkdir(parents=True, exist_ok=True)
        logging.info(f"write {str(ttl_file_path)}")
        with open(str(ttl_file_path), 'wb') as f:
            gzf = gzip.GzipFile(filename="", fileobj=f)
            gzf.write(buda_graph_ttl_str)
            gzf.close()
    return git_rev, buda_graph_ttl_str

def main(todoline):
    try:
        pecha_id = todoline[0]
        logging.info(f"BUDA import {pecha_id}")
        # the following call does the caching
        rev, buda_graph_ttl_str = get_graph_ttl_str(pecha_id) 
        if SEND_TO_BUDA:
            graph_uri = "http://purl.bdrc.io/graph/IE0OP"+pecha_id
            send_model_to_store(buda_graph_ttl_str, graph_uri)
        return [pecha_id, "ok", rev, datetime.now().isoformat()]
    except:
        logging.exception("BUDA import failed for " + todoline[0])
        return [pecha_id, "exception", "", datetime.now().isoformat()]


if __name__ == "__main__":
    # testing and debugging:
    #print(main(["I4D44D73F"]))
    # parallel run:
    ex = ParallelTaskExecutor("./todo-import.csv", "done-import-"+filesuffix+".csv", main)
    ex.run()