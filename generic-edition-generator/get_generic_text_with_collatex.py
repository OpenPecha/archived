import json
import tempfile
import subprocess

from pathlib import Path
from datetime import datetime
from horology import timed
from openpecha.core.pecha import OpenPechaFS
from openpecha.core.metadata import InitialPechaMetadata, InitialCreationType
from get_generic_txt_colletex import get_base_names, get_witnesses, fill_missing_witness, get_tokenized_witness, detokenize_witness, unicode_to_wyile, wyile_to_unicode

# @timed(unit='s', name="Compute collated text: ")
def get_collatex_output(witnesses_path):
    collatex_output = subprocess.check_output(f"java -jar collatex-tools-1.7.1.jar {str(witnesses_path)} -f csv")
    return collatex_output


def get_bases(base_name, witnesses):
    witness_bases = {
        "witnesses": []
    }
    for witness_id, witness in witnesses.items():
        
        witness_base = witness.read_base_file(base_name)
        tokenized_base = get_tokenized_witness(witness_base)
        cur_witness = {
            'id': witness_id,
            'content': tokenized_base
        }
        witness_bases["witnesses"].append(cur_witness)
    return witness_bases

def get_versions(segment, number_of_witnesses):
    versions = segment.split(",")
    versions = fill_missing_witness(versions, number_of_witnesses)
    return versions

def get_best_version(versions):
    if len(set(versions)) == len(versions):
        best_version = versions[0]
    else:   
        best_version = max(versions, key = versions.count)
    return best_version


def serialize_collatex_output(collatex_output, number_of_witnesses):
    generic_text = ""
    collatex_output = collatex_output.decode('utf-8')
    segments = collatex_output.splitlines()
    for segment in segments[1:]:
        versions = get_versions(segment, number_of_witnesses)
        elected_version = get_best_version(versions)
        generic_text += elected_version
    return generic_text

def get_collated_page(witness_pages):
    collatex_output_page = ""
    collatex_input_json = {
        'witnesses': []
    }
    for witness_id, witness_page in witness_pages.items():
        tokenized_page = get_tokenized_witness(witness_page)
        cur_witness = {
            'id': witness_id,
            'content': tokenized_page
        }
        collatex_input_json["witnesses"].append(cur_witness)
    collatex_input_json_obj = json.dumps(collatex_input_json)
    # with tempfile.TemporaryDirectory() as tmpdirname:
    # witness_combined_path = Path(tmpdirname) / "witnesses.json"
    witness_combined_path = Path('./witnesses.json')
    witness_combined_path.write_text(collatex_input_json_obj, encoding='utf-8')
    collatex_output_page = get_collatex_output("./witnesses.json")
    witness_combined_path.unlink()
    return collatex_output_page

def get_witness_pages(witness_pagination, witness_base):
    witness_pages = {}
    for uuid, page_annotation in witness_pagination['annotations'].items():
        img_num = page_annotation['imgnum']
        start = page_annotation['span']['start']
        end = page_annotation['span']['end']
        page_text = witness_base[start:end]
        witness_pages[img_num] = page_text
    return witness_pages

def get_cur_pages_of_witnesses(witnesses_pages, img_num):
    cur_pages_of_witnesses = {}
    for witness_id, witness_pages in witnesses_pages.items():
        cur_pages_of_witnesses[witness_id] = witness_pages.get(img_num, '')
    return cur_pages_of_witnesses


def get_witnesses_pages(witnesses, base_name):
    witnesses_pages = {}
    for witness_id, witness in witnesses.items():
        witness_base = witness.read_base_file(base_name)
        witness_pagination = witness.read_layers_file(base_name, "Pagination")
        witnesses_pages[witness_id] = get_witness_pages(witness_pagination, witness_base)
    return witnesses_pages


@timed(unit='s', name="Compute collated text: ")
def get_generic_base(base_name, witnesses, number_of_witnesses):
    generic_base = ""
    pagination_layer = witnesses['W1'].read_layers_file(base_name, "Pagination")
    witnesses_pages = get_witnesses_pages(witnesses, base_name)
    for uuid, page_annotation in pagination_layer['annotations'].items():
        imgnum = page_annotation['imgnum']
        witness_pages = get_cur_pages_of_witnesses(witnesses_pages, imgnum)
        collatex_output_page = get_collated_page(witness_pages)
        if collatex_output_page:
            generic_base += serialize_collatex_output(collatex_output_page, number_of_witnesses)
    
    generic_base = detokenize_witness(generic_base)
    return generic_base

def get_generic_text(witness_paths):
    generic_text = {}
    number_of_witnesses = len(witness_paths)
    witnesses = get_witnesses(witness_paths)

    reference_witness = witnesses['W1']
    ref_witness_base_names = get_base_names(reference_witness)
    for base_name in ref_witness_base_names:
        generic_text[base_name] = get_generic_base(base_name, witnesses, number_of_witnesses)
    return generic_text


if __name__ == "__main__":
    witness_paths = [
        Path('./test/opfs/I8B1FB7BB/I8B1FB7BB.opf'),
        Path('./test/opfs/IEA653111/IEA653111.opf'),
        Path('./test/opfs/I001/I001.opf'),
        Path('./test/opfs/I002/I002.opf'),
        Path('./test/opfs/I4DBEE949/I4DBEE949.opf'),
        Path('./test/opfs/I003/I003.opf')
    ]
    generic_text = get_generic_text(witness_paths)
    instance_meta = InitialPechaMetadata(
        initial_creation_type=InitialCreationType.ocr,
        created_at=datetime.now(),
        last_modified_at=datetime.now())
    generic_edition_pecha = OpenPechaFS()
    generic_edition_pecha._meta = instance_meta
    generic_edition_pecha.bases = generic_text
    generic_edition_pecha.save(output_path=Path('./data/opfs/generic_editions'))