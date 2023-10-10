"""This module for bdrc ocr functions.

This module contains all the functions required for
bdrc ocr pipeline

Availabel functions:
    download_func: download image from s3
    ocr_func: ocr the image
    upload_func: upload image and ocr ouput to s3
"""

import time

from .s3files import S3Image, S3OCROutput


def download_image(image: S3Image) -> S3Image:
    if not image: return
    time.sleep(2)
    print("downloaded:", image.local_path)
    return image

def ocr_image(image: S3Image) -> S3OCROutput:
    if not image: return
    time.sleep(4)
    output = S3OCROutput(
        name=image.name,
        upload_url=f"{image.name}) upload_url",
        local_path=f"ocrfile({image.name}).json"
    )
    print("ocred:", output.local_path)
    return output

def upload_file(file: S3OCROutput) -> str:
    if not file: return
    time.sleep(3)
    print("uploaded:", file.local_path)
    return f"done: {file.name}"
