from gettext import Catalog
import re
from pathlib import Path


from openpecha.utils import dump_yaml


def parse_pecha_info(pecha_info):
    pecha_info_parts = pecha_info.split(",")
    pecha_id = re.search("\[(.+?)\]", pecha_info_parts[0]).group(1)
    try:
        work_id = re.search("bdr:bdr:(.+)", pecha_info_parts[4]).group(1)
    except:
        work_id = ""
    return pecha_id, work_id

def parse_catalog(catalog, works):
    pecha_id_and_work_id = {}
    pecha_infos = catalog.splitlines()
    for pecha_info in pecha_infos:
        pecha_id, work_id = parse_pecha_info(pecha_info)
        if work_id in works:
            pecha_id_and_work_id[work_id] = pecha_id
    
    return pecha_id_and_work_id


if __name__ == "__main__":
    catalog = Path('./catalog.txt').read_text(encoding='utf-8')
    works = Path('./work_ids.txt').read_text(encoding='utf-8').splitlines()
    pecha_id_and_work_id = parse_catalog(catalog, works)
    dump_yaml(pecha_id_and_work_id, Path('./work_id_with_pecha_id.yml'))

