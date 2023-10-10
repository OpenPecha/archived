import argparse
import gzip
import hashlib
import io
import json
import logging
import shutil
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import List

import botocore
import pytz
import requests
from github.GithubException import GithubException
from img2opf.ocr import google_ocr
from openpecha.catalog.manager import CatalogManager
from openpecha.formatters import GoogleOCRFormatter
from openpecha.github_utils import delete_repo
from PIL import Image as PillowImage
from rdflib import URIRef

from . import config

# openpecha opf setup
catalog = CatalogManager(formatter=GoogleOCRFormatter())

# logging config
logging.basicConfig(
    filename="bdrc_ocr.log",
    format="%(asctime)s, %(levelname)s: %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
    level=logging.INFO,
)



def notifier(msg):
    logging.info(msg)


def get_value(json_node):
    if json_node["type"] == "literal":
        return json_node["value"]
    else:
        return config.NSM.qname(URIRef(json_node["value"]))


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
        logging.error(
            f"Volume Info Error: No info found for Work {work_prefix_url}: status code: {r.status_code}"
        )
        return
    # the result of the query is already in ascending volume order
    res = r.json()
    for b in res["results"]["bindings"]:
        volume_prefix_url = config.NSM.qname(URIRef(b["volid"]["value"]))
        yield {
            "vol_num": get_value(b["volnum"]),
            "volume_prefix_url": volume_prefix_url,
            "imagegroup": volume_prefix_url[4:],
        }


def get_s3_prefix_path(
    work_local_id, imagegroup, service=None, batch_prefix=None, data_types=None
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
    if service:
        batch_dir = f"{base_dir}/{service}/{batch_prefix}001"
        paths = {config.BATCH_PREFIX: batch_dir}
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
            logging.exception(f"The object does not exist, {s3path}")
        else:
            raise
    return


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
        logging.exception(f"Empty image: {output_fn}")
        return

    try:
        img.save(str(output_fn))
    except Exception as e:
        logging.exception(f"Image failed to save: {output_fn}")


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
    path_parts[1] = config.OUTPUT
    output_fn = Path("/".join(path_parts)) / f'{origfilename.split(".")[0]}.json.gz'
    if output_fn.is_file():
        return True

    return False


def save_images_for_vol(volume_prefix_url, work_local_id, imagegroup, images_base_dir, binarize):
    """
    this function gets the list of images of a volume and download all the images from s3.
    The output directory is output_base_dir/work_local_id/imagegroup
    """
    s3prefix = get_s3_prefix_path(work_local_id, imagegroup)
    for imageinfo in get_s3_image_list(volume_prefix_url):
        # if DEBUG['status'] and not imageinfo['filename'].split('.')[0] == 'I1KG35630002': continue
        imagegroup_output_dir = images_base_dir / work_local_id / imagegroup
        if image_exists_locally(imageinfo["filename"], imagegroup_output_dir):
            continue
        s3path = s3prefix + "/" + imageinfo["filename"]
        if config.DEBUG["status"]:
            print(f'\t- downloading {imageinfo["filename"]}')
        filebits = get_s3_bits(s3path, config.archive_bucket)
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
    images_dir = images_base_dir / work_local_id / imagegroup
    ocr_output_dir = ocr_base_dir / work_local_id / imagegroup
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
            logging.exception(f"Google OCR issue: {result_fn}")
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

    info = {"timestamp": now.split(".")[0], "imagesfolder": config.IMAGES}

    return info


def is_archived(key):
    try:
        config.S3_client.head_object(Bucket=config.OCR_OUTPUT_BUCKET, Key=key)
    except botocore.errorfactory.ClientError:
        return False
    return True


def archive_on_s3(images_base_dir, ocr_base_dir, work_local_id, imagegroup, s3_paths):
    """
    This function uploads the images on s3, according to the schema set up by BDRC, see documentation
    """
    # save info json
    info_json = get_info_json()
    s3_ocr_info_path = f"{s3_paths[config.BATCH_PREFIX]}/{config.INFO_FN}"
    config.ocr_output_bucket.put_object(
        Key=s3_ocr_info_path, Body=(bytes(json.dumps(info_json).encode("UTF-8")))
    )

    # archive images
    images_dir = images_base_dir / work_local_id / imagegroup
    if images_dir.is_dir():
        for img_fn in images_dir.iterdir():
            s3_image_path = f"{s3_paths[config.IMAGES]}/{img_fn.name}"
            if is_archived(s3_image_path):
                continue
            config.ocr_output_bucket.put_object(Key=s3_image_path, Body=img_fn.read_bytes())

    # archive ocr output
    ocr_output_dir = ocr_base_dir / work_local_id / imagegroup
    if ocr_output_dir.is_dir():
        for out_fn in ocr_output_dir.iterdir():
            s3_output_path = f"{s3_paths[config.OUTPUT]}/{out_fn.name}"
            if is_archived(s3_output_path):
                continue
            config.ocr_output_bucket.put_object(Key=s3_output_path, Body=out_fn.read_bytes())


def clean_up(data_path, work_local_id=None, imagegroup=None):
    """
    delete all the images and output of the archived volume (imagegroup)
    """
    if imagegroup:
        vol_image_path = data_path / config.IMAGES / work_local_id / imagegroup
        if vol_image_path.is_dir():
            shutil.rmtree(str(vol_image_path))
    elif work_local_id:
        work_output_path = data_path / config.OUTPUT / work_local_id
        if work_output_path.is_dir():
            shutil.rmtree(str(work_output_path))
    else:
        for path in data_path.iterdir():
            shutil.rmtree(str(path))


def get_work_local_id(work):
    if ":" in work:
        return work.split(":")[-1], work
    else:
        return work, f"bdr:{work}"


class OPFError(Exception):
    pass


def process_work(work, lang, binarize):
    if config.DEBUG["status"]:
        config.last_work, config.last_vol = work, "I1KG3563"
    work_local_id, work = get_work_local_id(work)

    is_work_empty = True
    is_start_work = True
    for i, vol_info in enumerate(get_volume_infos(work)):
        if (
            config.last_work == work_local_id
            and len(vol_info["imagegroup"]) == len(config.last_vol)
            and vol_info["imagegroup"] < config.last_vol
        ):
            continue

        is_work_empty = False

        # log work info at 1st vol
        if is_start_work and not config.DEBUG["status"]:
            notifier(f"`[Work-{config.HOSTNAME}]` _Work {work} processing ...._")
            is_start_work = False

        if not config.DEBUG["status"]:
            notifier(
                f'* `[Volume-{config.HOSTNAME}]` {vol_info["imagegroup"]} processing ....'
            )
        try:
            # save all the images for a given vol
            save_images_for_vol(
                volume_prefix_url=vol_info["volume_prefix_url"],
                work_local_id=work_local_id,
                imagegroup=vol_info["imagegroup"],
                images_base_dir=config.IMAGES_BASE_DIR,
                binarize=binarize
            )

            # apply ocr on the vol images
            apply_ocr_on_folder(
                images_base_dir=config.IMAGES_BASE_DIR,
                work_local_id=work_local_id,
                imagegroup=vol_info["imagegroup"],
                ocr_base_dir=config.OCR_BASE_DIR,
                lang=lang,
            )

            # get s3 paths to save images and ocr output
            s3_ocr_paths = get_s3_prefix_path(
                work_local_id=work_local_id,
                imagegroup=vol_info["imagegroup"],
                service=config.SERVICE,
                batch_prefix=config.BATCH_PREFIX,
                data_types=[config.IMAGES, config.OUTPUT],
            )

            # save image and ocr output at ocr.bdrc.org bucket
            archive_on_s3(
                images_base_dir=config.IMAGES_BASE_DIR,
                ocr_base_dir=config.OCR_BASE_DIR,
                work_local_id=work_local_id,
                imagegroup=vol_info["imagegroup"],
                s3_paths=s3_ocr_paths,
            )

            # delete the volume
            clean_up(
                config.DATA_PATH,
                work_local_id=work_local_id,
                imagegroup=vol_info["imagegroup"],
            )
        except:
            # create checkpoint
            save_check_point(imagegroup=f"{work_local_id}-{vol_info['imagegroup']}")
            raise RuntimeError

    if not is_work_empty:
        try:
            catalog.add_ocr_item(config.OCR_BASE_DIR / work_local_id)
            clean_up(config.DATA_PATH, work_local_id=work_local_id)
            clean_up(Path("./output"))
            save_check_point(work=work_local_id)
        except GithubException as ex:
            save_check_point(imagegroup=f"{work_local_id}-{vol_info['imagegroup']}")
            raise GithubException(ex.status, ex.data)
        except GeneratorExit:
            save_check_point(imagegroup=f"{work_local_id}-{vol_info['imagegroup']}")
            raise OPFError
    else:
        logging.warning(f"Empty work: {work_local_id}")


def get_work_ids(fn):
    for work in fn.read_text().split("\n"):
        if not work:
            continue
        yield work.strip()


def load_check_point():
    check_point = json.load(config.CHECK_POINT_FN.open())
    config.CHECK_POINT[config.WORK] = check_point[config.WORK]
    config.CHECK_POINT[config.VOL] = check_point[config.VOL]

    if config.CHECK_POINT[config.VOL]:
        config.last_work, config.last_vol = config.CHECK_POINT[config.VOL].split("-")


def save_check_point(work=None, imagegroup=None):
    if work and work not in config.CHECK_POINT[config.WORK]:
        config.CHECK_POINT[config.WORK].append(work)
    if imagegroup:
        config.CHECK_POINT[config.VOL] = imagegroup
    json.dump(config.CHECK_POINT, config.CHECK_POINT_FN.open("w"))


def show_error(ex, ex_type="ocr"):

    error = f"`Here's the error: {ex}"
    if ex_type == "ocr":
        error += f"\nTraceback: {traceback.format_exc()}`"
    logging.error(error)
    # notifier(f"`[ERROR] Error occured in {socket.gethostname()}`\n{error}")



def ocr_bdrc_work(works: List[str], batch_name: str, lang=None, binarize=False):

    notifier(f"`[OCR-{config.HOSTNAME}]` *Google OCR is running* ...")
    if config.CHECK_POINT_FN.is_file():
        load_check_point()
    for work_id in works:
        if config.CHECK_POINT[config.WORK] and work_id in config.CHECK_POINT[config.WORK]:
            continue
        try:
            process_work(work_id, lang=lang, binarize=binarize)
        except GithubException as ex:
            show_error(ex, ex_type="github")
            error_work = catalog.batch.pop()
            if catalog.batch:
                catalog.update()
            if error_work:
                delete_repo(error_work[0][1:8])
            # slack_notifier(f"`[Restart]` *{HOSTNAME}* ...")
        except OPFError:
            if catalog.batch:
                catalog.update()
            # slack_notifier(f"`[Restart]` *{HOSTNAME}* ...")
        except Exception as ex:
            show_error(ex)
            if catalog.batch:
                catalog.update()
            sys.exit()

        # update catalog every after 5 pecha
        if len(catalog.batch) == 5:
            catalog.update()

    notifier(f"[INFO] Completed {batch_name}")

    if catalog.batch:
        catalog.update()


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
    args = ap.parse_args()

    for works_path in Path(args.input_path).iterdir():
        works = get_work_ids(works_path)
        ocr_bdrc_work(works, works_path.name, lang=args.lang, binarize=args.binarize)
