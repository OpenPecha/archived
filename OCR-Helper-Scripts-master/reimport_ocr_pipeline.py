"""
Steps to reimport the ocr to openpecha-data:
1. create opf using the ocr output
2. check if existing work has opf in openpecha-data
3. if yes, download that opf
4. overwrite the newly fromatted opf to old opf repo
5. push the changes
6. if work has no opf in openpecha-data, publish the newly formatted opf to openpecha-data
"""

import os
import shutil
from datetime import datetime
import io
import os
import gzip
import json
import hashlib
import boto3
import botocore
import logging

from git import Repo 
from pathlib import Path
from datetime import datetime

from openpecha.core.ids import get_initial_pecha_id
from openpecha.formatters.ocr.google_vision import GoogleVisionFormatter, GoogleVisionBDRCFileProvider
from openpecha.formatters.ocr.hocr import HOCRBDRCFileProvider, HOCRFormatter
from openpecha.github_utils import create_release, create_github_repo, create_local_repo, commit, get_github_repo, update_github_repo_visibility
from openpecha.utils import load_yaml, dump_yaml
from openpecha.buda.api import get_buda_scan_info, image_group_to_folder_name

logfilesuffix = datetime.now().strftime("%Y%m%d-%H%M%S")
logging.basicConfig(filename='reimport_ocr-'+logfilesuffix+'.log', filemode='w', level=logging.INFO)

PUSH_REPOS = True
ORG_NAME = "Openpecha-data"

# TOKEN = Path('./secret.txt').read_text(encoding='utf-8').splitlines()[0]
TOKEN = "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"
PARSER_LINK = "https://github.com/OpenPecha/Toolkit/blob/7f57883d84bc10351527a49ee6ce970ace404e50/openpecha/formatters/google_ocr.py"

def create_opf(ocr_output, opf_dir, pecha_id, opf_import_options, ocr_import_info, buda_data):
    bdrc_scan_id = ocr_import_info['bdrc_scan_id']
    if ocr_import_info['software_id'] == "vision":
        data_provider =  GoogleVisionBDRCFileProvider(bdrc_scan_id, ocr_import_info, ocr_disk_path=ocr_output / "output")
        formatter = GoogleVisionFormatter(output_path=opf_dir)
        opf_path = formatter.create_opf(data_provider, pecha_id, opf_import_options, ocr_import_info)
    elif ocr_import_info['software_id'] == "google_books":
        data_provider = HOCRBDRCFileProvider(bdrc_scan_id, buda_data, ocr_import_info, ocr_disk_path=ocr_output)
        formatter = HOCRFormatter(output_path=opf_dir)
        opf_path = formatter.create_opf(data_provider, pecha_id, opf_import_options, ocr_import_info)
    return opf_path

def setup_auth(repo, org, token):
    remote_url = repo.remote().url
    old_url = remote_url.split("//")
    authed_remote_url = f"{old_url[0]}//{org}:{token}@{old_url[1]}"
    repo.remote().set_url(authed_remote_url)

def clean_dir(layers_output_dir):
    if layers_output_dir.is_dir():
        shutil.rmtree(str(layers_output_dir))

def publish_pecha(opf_path, asset_path, visibility):
    if not PUSH_REPOS:
        return
    repo_name = opf_path.name
    asset_paths = []
    commit_msg = "Create from OCR"
    private = visibility == "private"
    remote_repo_url = create_github_repo(opf_path, org_name=ORG_NAME, token=TOKEN, private=private)
    local_repo = create_local_repo(opf_path, remote_repo_url, org=ORG_NAME, token=TOKEN)
    commit(local_repo, commit_msg, not_includes=[])
    local_repo.git.checkout("-b", "review")
    local_repo.git.push("origin", "review")
    shutil.make_archive(asset_path, "zip", asset_path)
    asset_paths.append(f"{str(asset_path)}.zip")
    create_release(
        repo_name, prerelease=False, asset_paths=asset_paths, org=ORG_NAME, token=TOKEN
    )
    clean_dir(opf_path)
    clean_dir(asset_path)

Legacy_pecha_id_mapping = load_yaml(Path(f"./pecha_id_with_legacy_id.yml"))
def get_legacy_pecha_id(pecha_id):
    return Legacy_pecha_id_mapping.get(pecha_id)

def update_meta(pecha_path, new_opf_path):
    pecha_id = pecha_path.stem
    legacy_pecha_id = get_legacy_pecha_id(pecha_id)
    meta = load_yaml((new_opf_path / f"{new_opf_path.stem}.opf/meta.yml"))
    meta["last_modified"] = datetime.now()
    meta['legacy_id'] = legacy_pecha_id
    bases = meta['bases']
    for _, info in bases.items():
        info['legacy_id'] = f"v{info['order']:03}"
    meta_path = (pecha_path / f"{pecha_path.stem}.opf/meta.yml")
    dump_yaml(meta, meta_path)

def get_visibility(opf_path):
    meta = load_yaml((opf_path / f"{opf_path.stem}.opf/meta.yml"))
    if (meta["source_metadata"]["status"] != "http://purl.bdrc.io/admindata/StatusReleased"
        or meta["source_metadata"]["access"] != "http://purl.bdrc.io/admindata/AccessOpen"):
        return "private"
    return "public"

def update_original_pecha(pecha_path, new_opf_path, visibility):
    update_meta(pecha_path, new_opf_path)
    source_pecha_id = new_opf_path.stem
    source_opf_path = Path(f"{new_opf_path}/{source_pecha_id}.opf")
    target_pecha_id = pecha_path.stem
    target_opf_path = Path(f"{pecha_path}/{target_pecha_id}.opf")
    source_base_path = Path(f"{source_opf_path}/base")
    source_layers_path =  Path(f"{source_opf_path}/layers")
    target_base_path =  Path(f"{target_opf_path}/base")
    target_layers_path =  Path(f"{target_opf_path}/layers")
    os.system(f"rm -rf {target_base_path}")
    os.system(f"rm -rf {target_layers_path}")
    os.system(f"cp -R {source_base_path} {target_base_path}")
    os.system(f"cp -R {source_layers_path} {target_layers_path}")
    repo = Repo(pecha_path)
    commit_msg = "Re-import from OCR"
    setup_auth(repo, ORG_NAME, TOKEN)
    commit(repo, commit_msg, not_includes=[])
    update_github_repo_visibility(source_pecha_id, ORG_NAME, TOKEN, visibility == "private")
    
def get_branch(repo, branch):
    if branch in repo.heads:
        return branch
    return "master"

def download_old_pecha(pecha_id, out_path=None, branch="master"):
    pecha_url = f"https://github.com/Openpecha-data/{pecha_id}.git"
    out_path = Path(out_path)
    out_path.mkdir(exist_ok=True, parents=True)
    pecha_path = out_path / pecha_id
    Repo.clone_from(pecha_url, str(pecha_path))
    repo = Repo(str(pecha_path))
    branch_to_pull = get_branch(repo, branch)
    repo.git.checkout(branch_to_pull)
    logging.info(f"{pecha_id} downloaded ")
    return pecha_path 

class SimpleTaskTracker():
    """
    Very basic task tracker
    """

    def __init__(self, todo_csv_filename, done_csv_filename):
        self.todo_csv_filename = todo_csv_filename
        self.done_csv_filename = done_csv_filename
        self.todos = self._get_todos()

    def has_next(self):
        return len(self.todos) != 0

    def _get_todos(self):
        res = []
        with open(self.todo_csv_filename) as f:
            lines = f.readlines()
            for l in lines:
                res.append(l[:-1].split(","))
        logging.info("tracking %d imports" % len(res))
        return res

    def _update_todo(self):
        with open(self.todo_csv_filename, "w") as f:
            for t in self.todos:
                f.write(",".join(t)+"\n")

    def next_todo(self):
        todo = self.todos.pop(0)
        logging.info("starting import of %s (%s, %s)" % (todo[0], todo[1], todo[2]))
        return {"scan_id": todo[0], "service": todo[1], "batch": todo[2]}

    def set_done(self, scan_id, service, batch, pecha_id, status="ok"):
        logging.info("import of %s (%s, %s) into %s done with status %s" % (scan_id, service, batch, pecha_id, status))
        self._update_todo()
        my_date = datetime.now()
        with open(self.done_csv_filename, "a") as f:
            f.write(scan_id+","+service+","+batch+","+status+","+pecha_id+","+my_date.isoformat()+"\n")

class MockTaskTracker():
    """
    Use to test just one import
    """
    def __init__(self, scan_id, service, batch):
        self.todos = [[scan_id, service, batch]]

    def has_next(self):
        return len(self.todos) != 0

    def next_todo(self):
        todo = self.todos.pop(0)
        logging.info("starting import of %s (%s, %s)" % (todo[0], todo[1], todo[2]))
        return {"scan_id": todo[0], "service": todo[1], "batch": todo[2]}

    def set_done(self, scan_id, service, batch, pecha_id, status="ok"):
        logging.info("import of %s (%s, %s) into %s done with status %s" % (scan_id, service, batch, pecha_id, status))

def get_ocr_info(ocr_output_path):
    ocr_info_path = ocr_output_path / "info.json"
    with open(ocr_info_path) as jsonf:
        return json.load(jsonf)

ARCHIVE_BUCKET = "archive.tbrc.org"
OCR_OUTPUT_BUCKET = "ocr.bdrc.io"
S3 = boto3.resource("s3")
S3_client = boto3.client("s3")
archive_bucket = S3.Bucket(ARCHIVE_BUCKET)
ocr_output_bucket = S3.Bucket(OCR_OUTPUT_BUCKET)

def copy_one_file(s3key, dst_path, bucket):
    bucket.download_file(s3key, str(dst_path))

def copy_one_folder(s3_folder, dst_path, bucket):
    for obj in bucket.objects.filter(Prefix=s3_folder):
        target = obj.key if dst_path is None \
            else os.path.join(dst_path, os.path.relpath(obj.key, s3_folder))
        if os.path.isfile(target) or Path(target).name[-4:] == '.txt':
            continue
        bucket.download_file(obj.key, target)

def get_s3_bits(s3path, bucket):
    """
    get the s3 binary data in memory
    """
    f = io.BytesIO()
    try:
        bucket.download_fileobj(s3path, f)
        return f
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "404":
            logging.exception(f"The object does not exist, {s3path}")
        else:
            raise
    return

def md5_two(work_local_id):
    md5 = hashlib.md5(str.encode(work_local_id))
    return md5.hexdigest()[:2]

def get_s3_archive_image_prefix_path(scan_id, image_group_id):
    """
    the input is like W22084, I0886. The output is an s3 prefix ("folder"), the function
    can be inspired from
    https://github.com/buda-base/volume-manifest-tool/blob/f8b495d908b8de66ef78665f1375f9fed13f6b9c/manifestforwork.py#L94
    which is documented
    """
    two = md5_two(scan_id)
    vol_folder = image_group_to_folder_name(scan_id, image_group_id)
    return 'Works/{two}/{RID}/images/{vol_folder}/'.format(two=two, RID=scan_id, vol_folder=vol_folder)

def get_s3_image_list(scan_id, image_group_id):
    s3key = get_s3_archive_image_prefix_path(scan_id, image_group_id)+"dimensions.json"
    blob = get_s3_bits(s3key, archive_bucket)
    if blob is None:
        return None
    blob.seek(0)
    b = blob.read()
    ub = gzip.decompress(b)
    s = ub.decode('utf8')
    data = json.loads(s)
    return data

def image_filename_to_vision_ocr_filename(image_filename):
    return f"{image_filename.split('.')[0]}.json.gz"


def donwnload_ocr_in_cache(cache_path, scan_id, service, batch, buda_info, force=True):
    logging.info("download OCR output for %s (%s, %s)" % (scan_id, service, batch))
    two = md5_two(scan_id)
    scan_output_path = S3_CACHE_PATH / two / scan_id / service / batch
    scan_output_path.mkdir(parents=True, exist_ok=True)
    s3_key_prefix = "Works/%s/%s/%s/%s/" % (two, scan_id, service, batch)
    copy_one_file(s3_key_prefix+"info.json", scan_output_path / "info.json", ocr_output_bucket)
    for num, image_group_id in enumerate(buda_info["image_groups"]):
        logging.info("download OCR output for %s-%s (%s, %s)" % (scan_id, image_group_id, service, batch))
        image_list = get_s3_image_list(scan_id, image_group_id)
        vol_folder = image_group_to_folder_name(scan_id, image_group_id)
        s3_folder_key_prefix = s3_key_prefix + "output/" + vol_folder + "/"
        vol_output_path = scan_output_path / "output" / vol_folder
        vol_output_path.mkdir(parents=True, exist_ok=True)
        if service == "vision":
            for imageinfo in image_list:
                # TODO: handle service="google_ocr" here
                    vision_ocr_filename = image_filename_to_vision_ocr_filename(imageinfo["filename"])
                    output_path = vol_output_path / vision_ocr_filename
                    if (not force) and output_path.is_file():
                        continue
                    try:
                        copy_one_file(s3_folder_key_prefix+vision_ocr_filename, output_path, ocr_output_bucket)
                    except:
                        logging.warning("couldn't download OCR result %s, ignoring" % (s3_folder_key_prefix+vision_ocr_filename))
        elif service == "google_books":
            s3_info_folder_key_prefix = s3_key_prefix + "info/" + vol_folder 
            vol_info_path = scan_output_path / "info" / vol_folder
            vol_info_path.mkdir(parents=True, exist_ok=True)
            try:
                copy_one_folder(s3_folder_key_prefix, vol_output_path, ocr_output_bucket)
                copy_one_folder(s3_info_folder_key_prefix, vol_info_path, ocr_output_bucket)
            except:
                logging.warning("couldn't download OCR result %s, ignoring" % (s3_folder_key_prefix+vision_ocr_filename))

S3_CACHE_PATH = Path('./mnt/d/s3_res/')
NEW_OPF_TMP_DIR = Path("./mnt/d/opf/new_opf")
OLD_OPF_TMP_DIR = Path("./mnt/d/opf/old_opf")

OPF_IMPORT_OPTIONS = {}

def main(task_tracker):
    scan_id_and_pecha_id = load_yaml(Path('./work_id_with_pecha_id.yml'))
    while task_tracker.has_next():
        todo = task_tracker.next_todo()
        scan_id = todo["scan_id"]
        service = todo["service"]
        batch = todo["batch"]
        pecha_id = None
        has_existing_pecha = False
        if scan_id in scan_id_and_pecha_id:
            for pechainfo in scan_id_and_pecha_id[scan_id]:
                if pechainfo["service"] == service and pechainfo["batch"] == batch:
                    pecha_id = pechainfo["pecha"]
                    has_existing_pecha = True
                    break
        if pecha_id is None:
            pecha_id = get_initial_pecha_id()
            logging.info("no existing pecha for %s (%s, %s) recorded, creating a new one" % (scan_id, service, batch))
        two = md5_two(scan_id)
        ocr_output_path = S3_CACHE_PATH / two / scan_id / service / batch
        buda_info = get_buda_scan_info(scan_id)
        if not buda_info:
            logging.error("can't get buda info for "+scan_id)
            task_tracker.set_done(scan_id, service, batch, pecha_id, "error_no_buda_info")
            continue
        if not ocr_output_path.is_dir():
            donwnload_ocr_in_cache(S3_CACHE_PATH, scan_id, service, batch, buda_info)
        ocr_info = get_ocr_info(ocr_output_path)
        ocr_import_info = {
            "bdrc_scan_id": scan_id,
            "source": "bdrc",
            "ocr_info": ocr_info,
            "batch_id": batch,
            "software_id": service,
            "expected_default_language": "bo",
            "parser_link": PARSER_LINK
        }
        try:
            opf_path = create_opf(ocr_output_path, NEW_OPF_TMP_DIR, pecha_id, OPF_IMPORT_OPTIONS, ocr_import_info, buda_info)
            visibility = get_visibility(opf_path)
            if has_existing_pecha:
                old_pecha_path = download_old_pecha(pecha_id, out_path=OLD_OPF_TMP_DIR)
                update_original_pecha(old_pecha_path, opf_path, visibility)
            else:
                publish_pecha(opf_path, ocr_output_path, visibility)
            task_tracker.set_done(scan_id, service, batch, pecha_id)
        except:
            task_tracker.set_done(scan_id, service, batch, pecha_id, "exception")
            logging.exception("import of %s (%s, %s) into %s failed" % (scan_id, service, batch, pecha_id))

if __name__ == "__main__":
    main(SimpleTaskTracker("reimport_hocr_todo.txt", "reimport_hocr_done.txt"))
    # for testing:
    # main(MockTaskTracker("W00EGS1016246", "vision", "batch001"))
    # example of work id which doesn't have existing
#    main(MockTaskTracker("W8LS68018", "vision", "batch001")) 
   