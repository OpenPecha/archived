import argparse
from email.mime import base
import faulthandler
# from logging.config import _OptionalDictConfigArgs
# from wsgiref.simple_server import software_version

faulthandler.enable()

import gzip
import hashlib
import io
import json
import logging
import os
import shutil
import socket
import sys
import traceback
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import boto3
import botocore
import pytz
import rdflib
import requests
from github.GithubException import GithubException
# from img2opf.notifier import slack_notifier
from img2opf.ocr import google_ocr
from openpecha.catalog.manager import CatalogManager
from openpecha.formatters.ocr.google_vision import GoogleVisionFormatter
from openpecha.buda.api import get_s3_folder_prefix, image_group_to_folder_name
from openpecha.github_utils import delete_repo
from PIL import Image as PillowImage
from PIL import ImageOps
from rdflib import URIRef
from rdflib.namespace import Namespace, NamespaceManager
from wand.image import Image as WandImage

# Host config
HOSTNAME = socket.gethostname()

# S3 config
os.environ["AWS_SHARED_CREDENTIALS_FILE"] = "~/.aws/credentials"
ARCHIVE_BUCKET = "archive.tbrc.org"
OCR_OUTPUT_BUCKET = "ocr.bdrc.io"
S3 = boto3.resource("s3")
S3_client = boto3.client("s3")
archive_bucket = S3.Bucket(ARCHIVE_BUCKET)
ocr_output_bucket = S3.Bucket(OCR_OUTPUT_BUCKET)

# URI config
BDR = Namespace("http://purl.bdrc.io/resource/")
NSM = NamespaceManager(rdflib.Graph())
NSM.bind("bdr", BDR)

# s3 bucket directory config
SERVICE = "vision"
BATCH_PREFIX = 'batch'
IMAGES = 'images'
OUTPUT = 'output'
INFO_FN = "info.json"

# local directory config
DATA_PATH = Path("./archive")
IMAGES_BASE_DIR = DATA_PATH / IMAGES
OCR_BASE_DIR = DATA_PATH / OUTPUT
CHECK_POINT_FN = DATA_PATH / "checkpoint.json"

# Checkpoint config
CHECK_POINT = defaultdict(list)
COLLECTION = "collection"
WORK = "work"
VOL = "imagegroup"
last_work = None
last_vol = None

# notifier config
# notifier = slack_notifier

# openpecha opf setup
# Github Config
# os.environ["OPENPECHA_DATA_GITHUB_ORG"] = "Openpecha-Data"
catalog = CatalogManager(formatter=GoogleVisionFormatter())

# logging config
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s, %(levelname)s: %(message)s")
file_handler = logging.FileHandler("bdrc_ocr.log")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


# Debug config
DEBUG = {"status": False}


def notifier(msg):
    logger.info(msg)


def get_value(json_node):
    if json_node["type"] == "literal":
        return json_node["value"]
    else:
        return NSM.qname(URIRef(json_node["value"]))

def get_s3_prefix_path(
    work_local_id, imagegroup, service_id=None, batch_id=None, data_types=None
):
    """
    the input is like W22084, I0886. The output is an s3 prefix ("folder"), the function
    can be inspired from
    https://github.com/buda-base/volume-manifest-tool/blob/f8b495d908b8de66ef78665f1375f9fed13f6b9c/manifestforwork.py#L94
    which is documented
    """
    md5 = hashlib.md5(str.encode(work_local_id))
    two = md5.hexdigest()[:2]

    pre, rest = imagegroup[0], imagegroup[1:]
    if pre == "I" and rest.isdigit() and len(rest) == 4:
        suffix = rest
    else:
        suffix = imagegroup

    base_dir = f"Works/{two}/{work_local_id}"
    if service_id is not None:
        batch_dir = f"{base_dir}/{service_id}/{batch_id}"
        paths = {BATCH_PREFIX: batch_dir}
        for dt in data_types:
            paths[dt] = f"{batch_dir}/{dt}/{work_local_id}-{suffix}"
        return paths
    return f"{base_dir}/images/{work_local_id}-{suffix}"


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
            logger.exception(f"The object does not exist, {s3path}")
        else:
            raise
    return

def get_s3_image_list(volume_prefix_url):
    """
    returns the content of the dimension.json file for a volume ID, accessible at:
    https://iiifpres.bdrc.io/il/v:bdr:V22084_I0888 for volume ID bdr:V22084_I0888
    """
    r = requests.get(f"https://iiifpres.bdrc.io/il/v:{volume_prefix_url}")
    if r.status_code != 200:
        logging.error(
            f"Volume Images list Error: No images found for volume {volume_prefix_url}: status code: {r.status_code}"
        )
        return {}
    return r.json()

def get_volume_infos(work_prefix_url):
    """
    the input is something like bdr:W22084, the output is a list like:
    [
      {
        "vol_num": 1,
        "volume_prefix_url": "bdr:V22084_I0886",
        "imagegroup": "I0886"
      },
      ...
    ]
    """
    r = requests.get(
        f"http://purl.bdrc.io/query/table/volumesForWork?R_RES={work_prefix_url}&format=json&pageSize=500"
    )
    if r.status_code != 200:
        logger.error(
            f"Volume Info Error: No info found for Work {work_prefix_url}: status code: {r.status_code}"
        )
        return
    # the result of the query is already in ascending volume order
    res = r.json()
    for b in res["results"]["bindings"]:
        volume_prefix_url = NSM.qname(URIRef(b["volid"]["value"]))
        yield {
            "vol_num": get_value(b["volnum"]),
            "volume_prefix_url": volume_prefix_url,
            "imagegroup": volume_prefix_url[4:],
        }


def save_with_wand(bits, output_fn):
    try:
        with WandImage(blob=bits.getvalue()) as img:
            img.format = "png"
            img.save(filename=str(output_fn))
    except Exception as e:
        logger.exception(
            f"Error in saving: {output_fn} : origfilename: {output_fn.name}"
        )

def _binarize(img, th=127):
    return img.convert("L").point(lambda x: 255 if x > th else 0, mode='1')


def save_file(bits, origfilename, imagegroup_output_dir, binarize=False):
    """
    uses pillow to interpret the bits as an image and save as a format
    that is appropriate for Google Vision (png instead of tiff for instance).
    This may also apply some automatic treatment
    """
    imagegroup_output_dir.mkdir(exist_ok=True, parents=True)
    output_fn = imagegroup_output_dir / origfilename
    if Path(origfilename).suffix in [".tif", ".tiff", ".TIF"]:
        output_fn = imagegroup_output_dir / f'{origfilename.split(".")[0]}.png'
    if output_fn.is_file():
        return
    try:
        img = PillowImage.open(bits)
        if binarize:
            img = _binarize(img)
    except Exception as e:
        if bits.getvalue():
            save_with_wand(bits, output_fn)
        else:
            logger.exception(f"Empty image: {output_fn}")
        return

    try:
        img.save(str(output_fn))
    except:
        del img
        save_with_wand(bits, output_fn)


def image_exists_locally(origfilename, imagegroup_output_dir):
    if origfilename.endswith(".tif"):
        output_fn = imagegroup_output_dir / f'{origfilename.split(".")[0]}.png'
        if output_fn.is_file():
            return True
    else:
        output_fn = imagegroup_output_dir / origfilename
        if output_fn.is_file():
            return True

    # ocr output is processed
    path_parts = list(imagegroup_output_dir.parts)
    path_parts[1] = OUTPUT
    output_fn = Path("/".join(path_parts)) / f'{origfilename.split(".")[0]}.json.gz'
    if output_fn.is_file():
        return True

    return False


def save_images_for_vol(volume_prefix_url, work_local_id, imagegroup, images_base_dir, binarize):
    """
    this function gets the list of images of a volume and download all the images from s3.
    The output directory is output_base_dir/work_local_id/imagegroup
    """
    vol_folder = image_group_to_folder_name(work_local_id, imagegroup)
    s3prefix = get_s3_prefix_path(work_local_id, imagegroup)
    for imageinfo in get_s3_image_list(volume_prefix_url):
        # if DEBUG['status'] and not imageinfo['filename'].split('.')[0] == 'I1KG35630002': continue
        imagegroup_output_dir = images_base_dir / work_local_id / vol_folder
        if image_exists_locally(imageinfo["filename"], imagegroup_output_dir):
            continue
        s3path = s3prefix + "/" + imageinfo["filename"]
        if DEBUG["status"]:
            print(f'\t- downloading {imageinfo["filename"]}')
        filebits = get_s3_bits(s3path, archive_bucket)
        if filebits:
            save_file(filebits, imageinfo["filename"], imagegroup_output_dir, binarize=binarize)


def gzip_str(string_):
    # taken from https://gist.github.com/Garrett-R/dc6f08fc1eab63f94d2cbb89cb61c33d
    out = io.BytesIO()

    with gzip.GzipFile(fileobj=out, mode="w") as fo:
        fo.write(string_.encode())

    bytes_obj = out.getvalue()
    return bytes_obj


def apply_ocr_on_folder(images_base_dir, work_local_id, imagegroup, ocr_base_dir, lang):
    """
    This function goes through all the images of imagesfolder, passes them to the Google Vision API
    and saves the output files to ocr_base_dir/work_local_id/imagegroup/filename.json.gz
    """
    vol_folder = image_group_to_folder_name(work_local_id, imagegroup)
    images_dir = images_base_dir / work_local_id / vol_folder
    ocr_output_dir = ocr_base_dir / work_local_id / vol_folder
    ocr_output_dir.mkdir(exist_ok=True, parents=True)
    if not images_dir.is_dir():
        return
    for img_fn in images_dir.iterdir():
        result_fn = ocr_output_dir / f"{img_fn.stem}.json.gz"
        if result_fn.is_file():
            continue
        try:
            result = google_ocr(str(img_fn), lang_hint=lang)
        except:
            logger.exception(f"Google OCR issue: {result_fn}")
            continue
        result = json.dumps(result)
        gzip_result = gzip_str(result)
        result_fn.write_bytes(gzip_result)


def get_info_json():
    """
    This returns an object that can be serialied as info.json as specified for BDRC s3 storage.
    """
    # get current date and time
    now = datetime.now(pytz.utc).isoformat()

    info = {"timestamp": now.split(".")[0], "imagesfolder": IMAGES}

    return info


def is_archived(key):
    try:
        S3_client.head_object(Bucket=OCR_OUTPUT_BUCKET, Key=key)
    except botocore.errorfactory.ClientError:
        return False
    return True


def archive_on_s3(images_base_dir, ocr_base_dir, work_local_id, imagegroup, s3_paths, batch_id):
    """
    This function uploads the images on s3, according to the schema set up by BDRC, see documentation
    """
    # save info json
    info_json = get_info_json()
    s3_ocr_info_path = f"{s3_paths[BATCH_PREFIX]}/{INFO_FN}"
    ocr_output_bucket.put_object(
        Key=s3_ocr_info_path, Body=(bytes(json.dumps(info_json).encode("UTF-8")))
    )

    # archive images
    vol_folder = image_group_to_folder_name(work_local_id, imagegroup)
    
    if batch_id == "batch001":
        images_dir = images_base_dir / work_local_id / vol_folder
        if images_dir.is_dir():
            for img_fn in images_dir.iterdir():
                s3_image_path = f"{s3_paths[IMAGES]}/{img_fn.name}"
                if is_archived(s3_image_path):
                    continue
                ocr_output_bucket.put_object(Key=s3_image_path, Body=img_fn.read_bytes())

    # archive ocr output
    ocr_output_dir = ocr_base_dir / work_local_id / vol_folder
    if ocr_output_dir.is_dir():
        for out_fn in ocr_output_dir.iterdir():
            s3_output_path = f"{s3_paths[OUTPUT]}/{out_fn.name}"
            if is_archived(s3_output_path):
                continue
            ocr_output_bucket.put_object(Key=s3_output_path, Body=out_fn.read_bytes())


def clean_up(data_path, work_local_id=None, imagegroup=None):
    """
    delete all the images and output of the archived volume (imagegroup)
    """
    # vol_folder = image_group_to_folder_name(work_local_id, imagegroup)
    # if imagegroup:
    #     vol_image_path = data_path / IMAGES / work_local_id / vol_folder
    #     if vol_image_path.is_dir():
    #         shutil.rmtree(str(vol_image_path))
    # elif work_local_id:
    #     work_output_path = data_path / OUTPUT / work_local_id
    #     if work_output_path.is_dir():
    #         shutil.rmtree(str(work_output_path))
    # else:
    #     for path in data_path.iterdir():
    #         shutil.rmtree(str(path))


def get_work_local_id(work):
    if ":" in work:
        return work.split(":")[-1], work
    else:
        return work, f"bdr:{work}"


class OPFError(Exception):
    pass

def get_formatted_batch_id(batch_id: int):
    return f"batch{batch_id:03}"


def get_batch_id(work_local_id, imagegroup, volume_prefix_url):
    
    md5 = hashlib.md5(str.encode(work_local_id))
    two = md5.hexdigest()[:2]

    vol_folder = image_group_to_folder_name(work_local_id, imagegroup)
    pre, rest = imagegroup[0], imagegroup[1:]
    if pre == "I" and rest.isdigit() and len(rest) == 4:
        suffix = rest
    else:
        suffix = imagegroup
    base_dir = f"Works/{two}/{work_local_id}"
    first_img_filename = list(get_s3_image_list(volume_prefix_url))[0]['filename'].split('.')[0]
    
    for batch_id in range(1,1000):
        # Works/6b/W1PD95844/vision/batch001/output/W1PD95844-I1PD95846/I1PD958460001.json.gz
        s3_key = base_dir + "/" + SERVICE + "/" + get_formatted_batch_id(batch_id) + "/output/" + f"{vol_folder}" + "/" + f"{first_img_filename}.json.gz"
        if is_archived(s3_key):
            continue
        return get_formatted_batch_id(batch_id)
    

    
def process_work(work, lang, binarize, batch_id=None):
    image_group_list = list(Path(f"./list.txt").read_text(encoding='utf-8').splitlines())
    global last_work, last_vol

    if DEBUG["status"]:
        last_work, last_vol = work, "I1KG3563"
    work_local_id, work = get_work_local_id(work)
    
    if batch_id:
        batch_id = get_formatted_batch_id(batch_id)
    else:
        for _, vol_info in enumerate(get_volume_infos(work)):
            if vol_info["imagegroup"] in image_group_list:
                batch_id = get_batch_id(work_local_id, vol_info["imagegroup"], vol_info["volume_prefix_url"])
                break

    # batch_id = "batch003"
    is_work_empty = False
    is_start_work = True
    for i, vol_info in enumerate(get_volume_infos(work)):
        if (
            last_work == work_local_id
            and len(vol_info["imagegroup"]) == len(last_vol)
            and vol_info["imagegroup"] < last_vol
        ):
            continue

        is_work_empty = False

        # log work info at 1st vol
        if is_start_work and not DEBUG["status"]:
            notifier(f"`[Work-{HOSTNAME}]` _Work {work} processing ...._")
            is_start_work = False

        if not DEBUG["status"]:
            notifier(
                f'* `[Volume-{HOSTNAME}]` {vol_info["imagegroup"]} processing ....'
            )
        if work_local_id == "W1PD95844":
            if  not vol_info["imagegroup"] in image_group_list:
                continue
        try:
            # save all the images for a given vol
            save_images_for_vol(
                volume_prefix_url=vol_info["volume_prefix_url"],
                work_local_id=work_local_id,
                imagegroup=vol_info["imagegroup"],
                images_base_dir=IMAGES_BASE_DIR,
                binarize=binarize
            )

            # apply ocr on the vol images
            apply_ocr_on_folder(
                images_base_dir=IMAGES_BASE_DIR,
                work_local_id=work_local_id,
                imagegroup=vol_info["imagegroup"],
                ocr_base_dir=OCR_BASE_DIR,
                lang=['bo-t-i0-handwrit'],
            )

            # get s3 paths to save images and ocr output
            s3_ocr_paths = get_s3_prefix_path(
                work_local_id=work_local_id,
                imagegroup=vol_info["imagegroup"],
                service_id=SERVICE,
                batch_id=batch_id,
                data_types=[IMAGES, OUTPUT]
                
            )

            # save image and ocr output at ocr.bdrc.org bucket
            archive_on_s3(
                images_base_dir=IMAGES_BASE_DIR,
                ocr_base_dir=OCR_BASE_DIR,
                work_local_id=work_local_id,
                imagegroup=vol_info["imagegroup"],
                s3_paths=s3_ocr_paths,
                batch_id=batch_id
            )

            # delete the volume
            clean_up(
                DATA_PATH,
                work_local_id=work_local_id,
                imagegroup=vol_info["imagegroup"],
            )
        except:
            # create checkpoint
            save_check_point(imagegroup=f"{work_local_id}-{vol_info['imagegroup']}")
            raise RuntimeError

    if not is_work_empty:
        try:
            ocr_import_info = create_ocr_import_info(work_local_id, SERVICE, batch_id)
            catalog.add_ocr_item(OCR_BASE_DIR / work_local_id, ocr_import_info)
            clean_up(DATA_PATH, work_local_id=work_local_id)
            clean_up(Path("./output"))
            save_check_point(work=work_local_id)
        except Exception as e:
            print(e)
        except GithubException as ex:
            save_check_point(imagegroup=f"{work_local_id}-{vol_info['imagegroup']}")
            raise GithubException(ex.status, ex.data)
        except GeneratorExit:
            save_check_point(imagegroup=f"{work_local_id}-{vol_info['imagegroup']}")
            raise OPFError
    else:
        logger.warning(f"Empty work: {work_local_id}")

def create_ocr_import_info(work_id, service, batch):
    ocr_import_info = {
        "bdrc_scan_id": work_id,
        "source": "bdrc.io",
        "batch_id": batch,
        "software_id": service,
        "expected_default_language": "bo",
        "ocr_info": {}
    }
    return ocr_import_info
    

def get_work_ids(fn):
    for work in fn.read_text().split("\n"):
        if not work:
            continue
        yield work.strip()


def load_check_point():
    global last_work, last_vol
    check_point = json.load(CHECK_POINT_FN.open())
    CHECK_POINT[WORK] = check_point[WORK]
    CHECK_POINT[VOL] = check_point[VOL]

    if CHECK_POINT[VOL]:
        last_work, last_vol = CHECK_POINT[VOL].split("-")


def save_check_point(work=None, imagegroup=None):
    if work and work not in CHECK_POINT[WORK]:
        CHECK_POINT[WORK].append(work)
    if imagegroup:
        CHECK_POINT[VOL] = imagegroup
    json.dump(CHECK_POINT, CHECK_POINT_FN.open("w"))


def show_error(ex, ex_type="ocr"):

    error = f"`Here's the error: {ex}"
    if ex_type == "ocr":
        error += f"\nTraceback: {traceback.format_exc()}`"
    logger.error(error)
    # notifier(f"`[ERROR] Error occured in {socket.gethostname()}`\n{error}")




if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--input_path",
        type=str,
        default="./usage/bdrc/input",
        help="path with work ids text files",
    )
    ap.add_argument("--lang", type=str, help="langauge code of the document")
    ap.add_argument("--binarize", "-bn", action='store_true')
    ap.add_argument("--batch_id", type=int, help="Batch number for OCR run")
    args = ap.parse_args()

    notifier(f"`[OCR-{HOSTNAME}]` *Google OCR is running* ...")
    if CHECK_POINT_FN.is_file():
        load_check_point()
    
    for workids_path in Path(args.input_path).iterdir():
        for i, work_id in enumerate(get_work_ids(workids_path)):
            if CHECK_POINT[WORK] and work_id in CHECK_POINT[WORK]:
                continue
            try:
                process_work(work_id, lang=args.lang, binarize=args.binarize, batch_id=args.batch_id)
            except GithubException as ex:
                show_error(ex, ex_type="github")
                error_work = catalog.batch.pop()
                if catalog.batch:
                    catalog.update()
                if error_work:
                    delete_repo(error_work[0][1:8])
                # slack_notifier(f"`[Restart]` *{HOSTNAME}* ...")
                os.execv(f'{shutil.which("nohup")}', ["nohup", "sh", "run.sh", "&"])
            except OPFError:
                if catalog.batch:
                    catalog.update()
                # slack_notifier(f"`[Restart]` *{HOSTNAME}* ...")
                os.execv(f'{shutil.which("nohup")}', ["nohup", "sh", "run.sh", "&"])
            except Exception as ex:
                show_error(ex)
                if catalog.batch:
                    catalog.update()
                sys.exit()

            # update catalog every after 5 pecha
            if len(catalog.batch) == 5:
                catalog.update()

        notifier(f"[INFO] Completed {workids_path.name}")

    if catalog.batch:
        catalog.update()
