from pathlib import Path
from typing import List

from openpecha.core.pecha import OpenPechaFS

from collection.pecha import PechaCollection
from items.pecha import Pecha
from views.hfml import HFMLView, HFMLViewSerializer
from views.plain_base import PlainBaseView, PlainBaseViewSerializer
from views.view import View


def get_views() ->List[View]:
    views = [
        PlainBaseView(name='PlainBase', serializer_class=PlainBaseViewSerializer),
        HFMLView(name='HFML', serializer_class=HFMLViewSerializer)
    ]
    return views

def get_pecha(opf: OpenPechaFS) -> Pecha:
    
    pecha = Pecha(
        id = opf.pecha_id,
        title = opf.meta.source_metadata['text_title'],
        bdrc_id = opf.meta.source_metadata['bdrc_rid'],
        volume_number = opf.meta.source_metadata['pedurma_volume_number'],
        base_name = list(opf.components.keys())[0],
        pecha_path = opf.opf_path
    )

    return pecha


def get_pechas() -> List[Pecha]:
    pechas = []
    pecha_paths = list(Path('./data/non_derge_opfs/').iterdir())
    pecha_paths.sort()
    for pecha_path in pecha_paths:
        pecha_path = pecha_path / f"{pecha_path.stem}.opf"
        opf =OpenPechaFS(path=pecha_path, pecha_id=pecha_path.stem)
        pechas.append(get_pecha(opf))
    return pechas


def get_collection(collection_title: str, parent_dir: Path):
    views = get_views()
    pechas = get_pechas()

    collection = PechaCollection(
        title=collection_title,
        views=views,
        items=pechas,
        parent_dir=parent_dir
    )
    
    return collection

if __name__ == "__main__":
    collection_title = "Tengyur text not in Derge"
    parent_dir = Path('./data/')
    collection = get_collection(collection_title=collection_title, parent_dir=parent_dir)
    collection.save_collection()



