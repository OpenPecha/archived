
import os
from pathlib import Path

from bdrc_ocr import get_volume_infos, get_work_local_id, save_images_for_vol, apply_ocr_on_folder
from openpecha.utils import load_yaml

os.environ["AWS_SHARED_CREDENTIALS_FILE"] = "~/.aws/credentials"

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

def process(work_id, desired_imagegroup):
    bdrc_id = f"bdr:{work_id}"
    for vol_info in get_volume_infos(bdrc_id):
        imagegroup = vol_info["imagegroup"]
        if imagegroup == desired_imagegroup:
            print(f"[INFO] Downloading {imagegroup} images ....")
            save_images_for_vol(
                volume_prefix_url=vol_info["volume_prefix_url"],
                work_local_id=work_id,
                imagegroup=imagegroup,
                images_base_dir=IMAGES_BASE_DIR,
                binarize="-bn"
            )
            apply_ocr_on_folder(
                images_base_dir=IMAGES_BASE_DIR,
                work_local_id=work_id,
                imagegroup=vol_info["imagegroup"],
                ocr_base_dir=OCR_BASE_DIR,
                lang="bo-t-i0-handwrit",
            )

if __name__ == "__main__":
    work_infos =  load_yaml(Path(f"./work_info.yml"))
    for _, work_info in work_infos.items():
        work_id = work_info['work_id']
        desired_imagegroup = work_info['imagegroup']
        process(work_id, desired_imagegroup)
