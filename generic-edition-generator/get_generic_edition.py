import json
from pathlib import Path
from datetime import datetime
from horology import timed

from openpecha.core.pecha import OpenPechaFS
from openpecha.core.metadata import InitialPechaMetadata, InitialCreationType
from openpecha.utils import dump_yaml, download_pecha
from diff_layer import get_base_paths, get_diff_layer, serialize_combined_diff
from combine_diff_merger import merge_combine_diff

from diff_selector import get_combined_diff_layer

DEFAULT_PATH = Path('~/.openpecha/pechas/')
class GenericEditionGenerator:

    def __init__(self, pecha_ids={}, pecha_paths={}, output_path=DEFAULT_PATH) -> None:
        self.reference_pecha_id = pecha_ids.get('reference', "")
        self.witnesses_pecha_ids = pecha_ids.get('witnesses', [])
        self.reference_pecha_path = self.get_reference_pecha_path(pecha_paths)
        self.witnesses_pecha_paths = self.get_witnesses_pecha_paths(pecha_paths)
        self.output_path = output_path
    
    def get_reference_pecha_path(self, pecha_paths={}):
        reference_pecha_path = pecha_paths.get('reference', None)
        if not reference_pecha_path:
            reference_pecha_path = download_pecha(self.reference_pecha_id)
        return reference_pecha_path


    def get_witnesses_pecha_paths(self, pecha_paths={}):
        witnesses_pecha_paths = pecha_paths.get('witnesses', [])
        if not witnesses_pecha_paths:
            witnesses_pecha_paths = []
            for witness_pecha_id in self.witnesses_pecha_ids:
                witnesses_pecha_paths.append(download_pecha(witness_pecha_id))
        return witnesses_pecha_paths

    
    def get_witness_pechas(self):
        witness_pechas = []
        for witness_pecha_path in self.witnesses_pecha_paths:
            witness_pechas.append(OpenPechaFS(path=witness_pecha_path))
        return witness_pechas
    
    @timed(unit='s', name="Compute collated text: ")
    def get_generic_edition(self):
        reference_pecha = OpenPechaFS(path=self.reference_pecha_path)
        diff_layers = {}
        generic_edition = {}
        witness_pechas = self.get_witness_pechas()
        ref_witness_id = reference_pecha.pecha_id
        reference_pecha_base_paths = get_base_paths(reference_pecha.base_path)
        for reference_pecha_base_path in reference_pecha_base_paths:
            reference_base_text = reference_pecha_base_path.read_text(encoding="utf-8")
            for witness_pecha in witness_pechas:
                witness_base_text = witness_pecha.read_base_file(reference_pecha_base_path.stem)
                cur_diff_layer = get_diff_layer(reference_base_text, witness_base_text)
                diff_layers[witness_pecha.pecha_id] = cur_diff_layer
            combined_diff_layer = get_combined_diff_layer(ref_witness_id, diff_layers)
            combined_diff_layer = merge_combine_diff(combined_diff_layer, ref_witness_id)
            generic_base = serialize_combined_diff(combined_diff_layer, reference_base_text)
            generic_edition[reference_pecha_base_path.stem] = generic_base
        instance_meta = InitialPechaMetadata(
        initial_creation_type=InitialCreationType.ocr,
        created_at=datetime.now(),
        last_modified_at=datetime.now())
        generic_edition_pecha = OpenPechaFS()
        generic_edition_pecha._meta = instance_meta
        generic_edition_pecha.bases = generic_edition
        generic_edition_pecha.save(output_path=self.output_path)
        return generic_edition_pecha


if __name__ == "__main__":

    reference_opf_path = Path('./test/opfs/I003/I003.opf')
    witness_opf_paths = [
        Path('./test/opfs/I8B1FB7BB/I8B1FB7BB.opf'),
        Path('./test/opfs/IEA653111/IEA653111.opf'),
        Path('./test/opfs/I001/I001.opf'),
        Path('./test/opfs/I002/I002.opf'),
        Path('./test/opfs/I4DBEE949/I4DBEE949.opf')
        
    ]
    output_path = Path('./data/opfs/generic_editions')

    pecha_paths = {
        'reference': reference_opf_path,
        'witnesses': witness_opf_paths
    }

    pecha_ids = {
        'reference': 'I4DBEE949',
        'witnesses': [
            'I8B1FB7BB',
            'IEA653111'
        ]
    }

    generic_edition_generator = GenericEditionGenerator(
        pecha_ids= pecha_ids,
        pecha_paths=pecha_paths,
        output_path=output_path
    )

    

    generic_edition = generic_edition_generator.get_generic_edition()
