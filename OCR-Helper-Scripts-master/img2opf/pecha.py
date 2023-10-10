import logging
from typing import Dict

import requests

from . import config


class Pecha:
    def __init__(self, images_dir=config.IMAGES_DIR, output_dir=config.OUTPUT_DIR):
        self.images_dir = images_dir
        self.output_dir = output_dir

    @property
    def volumes(self):
        return self._get_volumes()

    def _get_volumes(self):
        raise NotImplemented()

    def ocr(self):
        for volume in self.volumes:
            volume.get_images()
            volume.run_ocr()
            volume.archive()

class BDRCPecha(Pecha):
    def __init__(self, work_id):
        self.work_id = work_id
        volumes_url = (
            f"purl.bdrc.io/query/table/volumesForInstance?R_RES=bdr:M{self.work_id}&pageSize=500&format=json"
        )

    def _get_volumes(self):
        pass

class Volume:
    def get_images(self):
        raise NotImplementedError


class BDRCVolume(Volume):

    def __init__(self, prefix: str):
        self.prefix = prefix

    def get_images(self):
        r = requests.get(f"https://iiifpres.bdrc.io/il/v:{self.prefix}")
        if r.status_code != 200:
            logging.error(
                f"Volume Images list Error: No images found for volume {self.prefix}: status code: {r.status_code}"
            )
            return {}
        return r.json()

class Image:

    @property
    def url(self):
        raise NotImplementedError

class BDRCS3Image(Image):

    def __init__(self, prefix: str, file: Dict):
        self.prefix = prefix
        self.file = file

    @property
    def url(self):
        return f"{self.prefix}/{self.file['filename']}"
