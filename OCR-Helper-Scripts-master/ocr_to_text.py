from base64 import encode
from pathlib import Path
import json
import gzip
from openpecha.formatters.ocr.google_vision import GoogleVisionBDRCFileProvider, GoogleVisionFormatter


ocr_path = Path(f'./OCR_request/output/')
text_path = Path(f'./OCR_request/text/')


work_ids = ["W1KG12589", "W1KG16449", "W1PD192036", "W21521"]
image_groups = ["I1KG12592", "I1KG16485", "I2PD17744", "I0604"]
image_filenames = ["I1KG125920015.jpg", "I1KG164850012.jpg", "I2PD177440009.png", "06040010.png"]

def get_ocr(work_id, imagegroup, image_id):
    expected_ocr_filename = image_id[:image_id.rfind('.')]+".json.gz"
    expected_ocr_path = ocr_path / work_id / f"{work_id}-{imagegroup}" / expected_ocr_filename
    ocr_object = None
    try:
        ocr_object = json.load(gzip.open(str(expected_ocr_path), "rb"))
        page_content = ocr_object["textAnnotations"][0]["description"]
        return page_content
    except:
        print("could not read "+str(expected_ocr_path))
        return 


if __name__ == '__main__':
    for num, work_id in enumerate(work_ids):
    # num = 3
    # work_id = work_ids[num]
        imagegroup = image_groups[num]
        image_filename = image_filenames[num]
        output_path = text_path / work_id
        page_content = get_ocr(work_id, imagegroup, image_filename)
        filename= image_filename[:image_filename.rfind('.')]+".txt"
        work_path = Path(text_path) / work_id
        work_path.mkdir(exist_ok=True, parents=True)
        page_path = Path(work_path) / filename
        page_path.write_text(page_content, encoding='utf-8')
            