from pathlib import Path
import io
from openpecha.formatters.ocr.google_vision import GoogleVisionFormatter, GoogleVisionBDRCFileProvider
from openpecha.core.ids import get_initial_pecha_id
from usage.bdrc.bdrc_ocr import apply_ocr_on_folder
from img2opf.ocr import google_ocr
from usage.bdrc.bdrc_ocr import save_images_for_vol, get_volume_infos






IMAGES = "images"
OUTPUT = "output"


DATA_PATH = Path("./archive")
IMAGES_BASE_DIR = DATA_PATH / IMAGES
OCR_BASE_DIR = DATA_PATH / OUTPUT

from openpecha.buda.api import image_group_to_folder_name
from openpecha.utils import load_yaml
import logging
import json
import gzip

class GoogleVisionTestFileProvider():
    def __init__(self, bdrc_scan_id, bdrc_image_list_path, buda_data, ocr_import_info, ocr_disk_path):
        self.ocr_import_info = ocr_import_info
        self.ocr_disk_path = ocr_disk_path
        self.bdrc_scan_id = bdrc_scan_id
        self.buda_data = buda_data
        self.bdrc_image_list_path = bdrc_image_list_path

    def get_image_list(self, image_group_id):
        bdrc_image_list = load_yaml(self.bdrc_image_list_path / str(image_group_id+".json"))
        return map(lambda ii: ii["filename"], bdrc_image_list)

    def get_source_info(self):
        return self.buda_data

    def get_image_data(self, image_group_id, image_id):
        vol_folder = image_group_to_folder_name(self.bdrc_scan_id, image_group_id)
        expected_ocr_filename = image_id[:image_id.rfind('.')]+".json.gz"
        image_ocr_path = self.ocr_disk_path / vol_folder / expected_ocr_filename
        ocr_object = None
        try:
            ocr_object = json.load(gzip.open(str(image_ocr_path), "rb"))
        except:
            logging.exception("could not read "+str(image_ocr_path))
        return ocr_object
    
def gzip_str(string_):
    # taken from https://gist.github.com/Garrett-R/dc6f08fc1eab63f94d2cbb89cb61c33d
    out = io.BytesIO()

    with gzip.GzipFile(fileobj=out, mode="w") as fo:
        fo.write(string_.encode())

    bytes_obj = out.getvalue()
    return bytes_obj

if __name__ == "__main__":
    # lang = []
    # vol_info = ["I1PD95852"]
    lang = None
    work_ids = ["W1KG12589", "W1KG16449", "W1PD192036", "W21521"]
    image_groups = ["I1KG12592", "I1KG16485", "I2PD17744", "I0604"]
    # vol_infos = get_volume_infos(f"bdr:{work_local_id}")
    # # ocr_path = Path(f"./archive/output/W1PD95844")
    images_base_dir = Path(f"./OCR_request/images/")
    ocr_base_dir = Path(f"./OCR_request/output/")
    # ocr_import_info = {
    #     'source': 'bdrc',
    #     'software': 'google_vision',
    #     'batch': 'batch_2022',
    #     'expected_default_language': 'bo',
    #     'bdrc_scan_id':'W2PD17457'
    # }
    # for vol_info in vol_infos:
    #     imagegroup = vol_info['imagegroup']
    #     if imagegroup == "I1PD95852":
    #         apply_ocr_on_folder(
    #             images_base_dir=IMAGES_BASE_DIR,
    #             work_local_id=work_local_id,
    #             imagegroup=imagegroup,
    #             ocr_base_dir=OCR_BASE_DIR,
    #             lang='und-t-i0-handwrit',
    #         )
    for num, work_local_id in enumerate(work_ids):
        imagegroup  = image_groups[num]
        images_dir = images_base_dir / work_local_id / f"{work_local_id}-{imagegroup}"
        ocr_output_dir = ocr_base_dir / work_local_id / f"{work_local_id}-{imagegroup}"
        ocr_output_dir.mkdir(exist_ok=True, parents=True)
        for img_fn in images_dir.iterdir():
            result_fn = ocr_output_dir / f"{img_fn.stem}.json.gz"
            if result_fn.is_file():
                continue
            try:
                result = google_ocr(str(img_fn), lang_hint=lang)
            except:
                print(f"Google OCR issue: {result_fn}")
                continue
            result = json.dumps(result)
            gzip_result = gzip_str(result)
            result_fn.write_bytes(gzip_result)

    # bdrc_image_list_path = Path(f"{ocr_path}")
    # data_provider = GoogleVisionTestFileProvider(work_local_id, bdrc_image_list_path, ocr_import_info, ocr_path)
    # ocr = GoogleVisionFormatter(output_path=new_opf_path)
    # new_pecha_path = ocr.create_opf(data_provider, pecha_id, {}, ocr_import_info)
    # out_path = Path(f"./")