import csv
from pathlib import Path
from typing import List

from openpecha.core.pecha import OpenPechaFS

from items.pecha import Pecha
from views.view import View, ViewSerializer



class PlainBaseViewSerializer(ViewSerializer):

    def serialize(self, pecha: Pecha, output_dir: Path):
        opf_obj = OpenPechaFS(path=pecha.pecha_path)
        for base_name, base_components in opf_obj.components.items():
            base_text = opf_obj.get_base(base_name)
            (output_dir / f"{base_name}.txt").write_text(base_text, encoding='utf-8')

class PlainBaseView(View):

    def __init__(self, name: str, serializer_class: ViewSerializer) -> None:
        super().__init__(name, serializer_class)

    def save_catalog(self, collection_dir: Path, items: List[Pecha]):
        catalog_file_path = collection_dir / f"Catalog_{self.name}.csv"
        field_names = ['FILE NAME', 'TITLE', 'OP ID', 'BDRC ID', 'VOLUME NUMBER']
        items = []
        for item in items:
            cur_item_infos = [
                item.base_name,
                item.title,
                item.id,
                item.bdrc_id,
                item.volume_number
            ]
            items.append(cur_item_infos)
        with open(catalog_file_path, 'w') as csvfile:
            csvwriter = csv.writer(csvfile)   
            csvwriter.writerow(field_names) 
        
            # writing the data rows 
            csvwriter.writerows(items)
        
