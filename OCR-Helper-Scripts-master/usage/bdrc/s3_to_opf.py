import logging
import logging.config
from pathlib import Path
from re import S
from bdrc_ocr import (
    DEBUG,
    IMAGES_BASE_DIR,
    OCR_BASE_DIR,
    OUTPUT,
    get_s3_bits,
    get_s3_image_list,
    get_s3_prefix_path,
    get_volume_infos,
    get_work_local_id,
    ocr_output_bucket,
    save_images_for_vol,
)
from usage.bdrc.bdrc_ocr import SERVICE


# logging config
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s, %(levelname)s: %(message)s")
file_handler = logging.FileHandler("s3_download_issue.log")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

DEBUG["status"] = True


def save_json_output(bits, fn, output_dir):
    output_dir.mkdir(exist_ok=True, parents=True)
    output_fn = output_dir / fn
    output_fn.write_bytes(bits.getvalue())


def download_ocr_output_for_vol(
    volume_prefix_url, work_local_id, imagegroup, ocr_base_dir, service_id, batch_id
):
    
    ocr_output_dir = ocr_base_dir / work_local_id / imagegroup
    s3prefix = get_s3_prefix_path(
        work_local_id,
        imagegroup,
        service_id=service_id,
        batch_id=batch_id,
        data_types=[OUTPUT],
    )
    
    s3_image_list = get_s3_image_list(volume_prefix_url)
    if ocr_output_dir.is_dir() and len(list(ocr_output_dir.iterdir())) == len(s3_image_list):
        return
    (ocr_base_dir / work_local_id / imagegroup).mkdir(exist_ok=True, parents=True)
    for imageinfo in s3_image_list:
        ocr_json_fn = f"{imageinfo['filename'].split('.')[0]}.json.gz"
        if (ocr_output_dir / ocr_json_fn).is_file():
            continue
        s3path = s3prefix[OUTPUT] + "/" + ocr_json_fn
        filebits = get_s3_bits(s3path, ocr_output_bucket)
        if filebits:
            print(f"\t- downloading {ocr_json_fn}")
            save_json_output(filebits, ocr_json_fn, ocr_output_dir)
        else:
            logger.warning(f"{work_local_id} image group {imagegroup} has s3 download issue")
            break
            


def process_work(work, vols=None):
    work_local_id, work = get_work_local_id(work)

    is_work_empty = True
    for vol_info in get_volume_infos(work):
        is_work_empty = False
        print(f'[INFO] {vol_info["imagegroup"]} processing ....')

        # if vols and vol_info["imagegroup"] not in vols:
        #     continue

        # save_images_for_vol(
        #     volume_prefix_url=vol_info["volume_prefix_url"],
        #     work_local_id=work_local_id,
        #     imagegroup=vol_info["imagegroup"],
        #     images_base_dir=IMAGES_BASE_DIR,
        # )

        download_ocr_output_for_vol(
            volume_prefix_url=vol_info["volume_prefix_url"],
            work_local_id=work_local_id,
            imagegroup=vol_info["imagegroup"],
            ocr_base_dir=OCR_BASE_DIR,
            service_id=SERVICE,
            batch_id="batch001"
        )

    # if not is_work_empty:
    #    catalog.ocr_to_opf(OCR_BASE_DIR / work_local_id)

def parse_text_id_info(text_id_info):
    infos = text_id_info.split(",")
    work_infos = infos[0].split("-")
    work_id = work_infos[0]
    img_grp = [work_infos[1]]
    return work_id, img_grp


def get_s3_resources():
    work_ids = Path('./work_ids.txt').read_text(encoding='utf-8').splitlines()
    for work_id in work_ids:
        if work_id == "W20571":
            process_work(work_id)
    pass

if __name__ == "__main__":
    # process_work('W1PD95844')
    # process_work("W22069", ["I1KG17273"])
    # get_s3_resources()
    work_id = "W1PD95844"
    process_work(work_id)