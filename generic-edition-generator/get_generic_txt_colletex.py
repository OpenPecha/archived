import pyewts
import re

from bs4 import BeautifulSoup
from botok.tokenizers.wordtokenizer import WordTokenizer
# from pycollatex import *
from collatex import *
from datetime import datetime
from horology import timed
from openpecha.core.pecha import OpenPechaFS
from openpecha.core.metadata import InitialPechaMetadata, InitialCreationType
from pathlib import Path


# WT = WordTokenizer()

CONVERTER = pyewts.pyewts()

def unicode_to_wyile(unicode_text):
    wyile_text = CONVERTER.toWylie(unicode_text)
    return wyile_text

def wyile_to_unicode(wyile_text):
    unicode_text = CONVERTER.toUnicode(wyile_text)
    return unicode_text

# @timed(unit='s', name="Tokenization collated text: ")
def get_tokenized_witness(witness):
    witness = witness.replace(" ", "𰵀")
    witness = witness.replace("\n", "𰵁")
    tokenized_witness = re.sub("(་|།)", "\g<1> ", witness)
    # tokens = WT.tokenize(witness)
    # for token in tokens:
    #     tokenized_witness += f"{token.text} "
    return tokenized_witness

# @timed(unit='s', name="Detokenization collated text: ")
def detokenize_witness(tokenized_witness):
    detokenized_text = tokenized_witness.replace(" ", "")
    detokenized_text = detokenized_text.replace("𰵀", " ")
    detokenized_text = detokenized_text.replace("𰵁", "\n")
    return detokenized_text

@timed(unit='s', name="Compute collated text: ")
def get_collated_base(witness_bases):
    collation = Collation()
    for witness_id, witness_base in witness_bases.items():
        if witness_base:
            tokenized_witness = get_tokenized_witness(witness_base)
            wyile_tokenized_witness = unicode_to_wyile(tokenized_witness)
            collation.add_plain_witness(witness_id, wyile_tokenized_witness)
    return collate(collation, output="xml")

def fill_missing_witness(witnesses, number_of_witnesses):
    new_witnesses = []
    for witness in witnesses:
        new_witnesses.append(witness)
    for walker in range(0, number_of_witnesses-len(witnesses)):
        new_witnesses.append("")
    return new_witnesses

def get_witnesses_text(witnesses):
    witnesses_text = []
    for witness in witnesses:
        witnesses_text.append(witness.text)
    return witnesses_text


def get_generic_segment(segment, number_of_witnesses):
    generic_segment = ""
    witnesses = segment.find_all("rdg")
    witnesses_text = get_witnesses_text(witnesses)
    if len(witnesses_text) < number_of_witnesses:
        witnesses_text = fill_missing_witness(witnesses_text, number_of_witnesses)
    if len(set(witnesses_text)) == number_of_witnesses:
        generic_segment = witnesses_text[0]
    else:   
        generic_segment = max(witnesses_text, key = witnesses_text.count)
    return generic_segment

def get_witnesses(witness_paths):
    witnesses = {}
    for witness_walker, witness_path in enumerate(witness_paths, 1):
        witnesses[f"W{witness_walker}"] = OpenPechaFS(path=witness_path)
    return witnesses

def get_base_names(pecha):
    base_names = []
    base_paths = list((pecha.pecha_path / f"{pecha.pecha_path.stem}.opf" / "base").iterdir())
    for base_path in base_paths:
        base_names.append(base_path.stem)
    base_names.sort()
    return base_names


def get_witness_bases(base_name, witnesses):
    witness_bases = {}
    for witness_id, witness in witnesses.items():
        cur_base_text = witness.read_base_file(base_name)
        witness_bases[witness_id] = cur_base_text
    return witness_bases

def serialize_collatex_output(collated_text, number_of_witnesses):
    generic_text = ''
    soup = BeautifulSoup(collated_text, "html.parser")
    segments = soup.find_all("app")
    for segment in segments:
        generic_text += get_generic_segment(segment, number_of_witnesses)
    return generic_text


def get_generic_base(base_name, witnesses, number_of_witnesses):
    generic_base = ""
    witness_bases = get_witness_bases(base_name, witnesses)
    collated_base = get_collated_base(witness_bases)   
    generic_base = serialize_collatex_output(collated_base, number_of_witnesses)
    generic_base = wyile_to_unicode(generic_base)
    generic_base = detokenize_witness(generic_base)
    
    return generic_base




@timed(unit='min', name="Generic text overall: ")
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
        Path('./test/data/opfs/IEA653111/IEA653111.opf'),
        Path('./test/data/opfs/I8B1FB7BB/I8B1FB7BB.opf'),
        Path('./test/data/opfs/I4DBEE949/I4DBEE949.opf'),
    ]
    generic_text = get_generic_text(witness_paths)
    # instance_meta = InitialPechaMetadata(
    #     initial_creation_type=InitialCreationType.ocr,
    #     created_at=datetime.now(),
    #     last_modified_at=datetime.now())
    # generic_edition_pecha = OpenPechaFS()
    # generic_edition_pecha._meta = instance_meta
    # generic_edition_pecha.bases = generic_text
    # generic_edition_pecha.save(output_path=Path('./data/opfs/generic_editions'))
