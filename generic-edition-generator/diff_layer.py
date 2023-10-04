import re
import json

import requests

from antx.core import transfer
from fast_diff_match_patch import diff
from pathlib import Path
from openpecha.utils import dump_yaml, load_yaml
from diff_layer_parser import parse_diff_layer
from diff_selector import reformat_combined_diff_layer

def get_diffs(txt_1, txt_2):
    diffs = diff(txt_1, txt_2, counts_only = False)
    return diffs

def normalise_text(text):
    text = text.replace("\n", "#")
    text = text.replace(",", "་")
    return text

def get_syls(text):
    chunks = re.split('(་|།།|།)',text)
    syls = []
    cur_syl = ''
    for chunk in chunks:
        if re.search('་|།།|།',chunk):
            cur_syl += chunk
            syls.append(cur_syl)
            cur_syl = ''
        else:
            cur_syl += chunk
    if cur_syl:
        syls.append(cur_syl)
    return syls

def is_punct_diffs(diff_text):
    punct_diffs = ["[་,༌]", "[་,། ]", '[།,    ]']
    for punct_diff in punct_diffs:
        if diff_text == punct_diff:
            return True
    return False

def reformat_diff_text_from_right(diff_text, right_diff_text, second_right_diff, diffs, diff_walker):
    reformated_diff_text = f"[{diff_text},{right_diff_text}]"
    if is_punct_diffs(reformated_diff_text):
        return diff_text,diffs
    sr_diff_type, sr_diff_text = second_right_diff
    if second_right_diff == ["=", ""]:
        return reformated_diff_text, diffs
    if sr_diff_type == "=":
        if sr_diff_text[0] == "་":
            reformated_diff_text = f"[{diff_text}་,{right_diff_text}་]"
            diffs[diff_walker+2][1] = sr_diff_text[1:]
        elif diff_text[-1] != "་" or diff_text[-1] != "།" or diff_text[-1] != "༌":
            syls = get_syls(sr_diff_text)
            first_syl = syls[0]
            reformated_diff_text = f"[{diff_text}{first_syl},{right_diff_text}{first_syl}]"
            diffs[diff_walker+2][1] = "".join(syls[1:])
    return reformated_diff_text, diffs

def process_diff_text(chunk):
    reformated_diff = ""
    src_diff = re.search("\[(.+?),.+?\]", chunk).group(1)
    trg_diff = re.search("\[.+?,(.+?)\]", chunk).group(1)
    try:
        non_note_part = re.search("(.+)\[", chunk).group(1)
    except:
        non_note_part = ""
    if not non_note_part or non_note_part[-1] == "་" or non_note_part[-1] == "།" or non_note_part[-1] == " ":
        return chunk
    else:
        syls = get_syls(non_note_part)
        last_syl = syls[-1]
        reformated_diff = "".join(syls[:-1]) + f"[{last_syl}{src_diff},{last_syl}{trg_diff}]"
    return reformated_diff



def reformat_diff_text_from_left(text_with_diffs):
    text_with_diffs = re.sub("(\[.+?,.+?\])", "\g<1>\n", text_with_diffs)
    chunks = text_with_diffs.splitlines()
    reformated_diff_text = ""
    for chunk in chunks:
        if re.search('\[.+?,.+?\]', chunk):
            reformated_diff_text += process_diff_text(chunk)
        else:
            reformated_diff_text += chunk
    return reformated_diff_text

def reformat_continues_diff(text_with_diffs):
    reformated_text_with_diffs = text_with_diffs
    reformated_text_with_diffs = re.sub("\[([^\[|\]]+?),([^\]]+?)\]\[([^\[|\]]+?),([^\]]+?)\]", "[\g<1>\g<3>,\g<2>\g<4>]", reformated_text_with_diffs)
    return reformated_text_with_diffs

def rm_punct_note_text(oe_with_diffs):
    diffs = re.findall("\[.+?,.+?\]", oe_with_diffs)
    for diff in diffs:
        src_txt = re.search("\[(.+),", diff).group(1)
        trg_txt = re.search(",(.+)\]", diff).group(1)
        norm_src_txt = src_txt.replace(" ", "")
        norm_trg_txt = trg_txt.replace(" ", "")
        if norm_src_txt == norm_trg_txt:
            oe_with_diffs = oe_with_diffs.replace(diff, src_txt)
    return oe_with_diffs

def parse_diffs(diffs):
    oe_with_diffs = ""
    diffs = list(diffs)
    diff_list = []
    for diff in diffs:
        diff_list.append(list(diff))

    # left_diff = diffs[0]
    for diff_walker, (diff_type, diff_text) in enumerate(diff_list, 0):
        try:
            right_diff_type, right_diff_text = diff_list[diff_walker+1]
        except:
            right_diff_type, right_diff_text = ["=", ""]
        if diff_type == "=":
            oe_with_diffs += diff_text
        elif diff_type == "-":
            if right_diff_type == "+" and "༑" not in right_diff_text:
                try:
                    second_right_diff = diff_list[diff_walker+2]
                except:
                    second_right_diff = ["=", ""]
                reformated_diff_text, diff_list = reformat_diff_text_from_right(diff_text, right_diff_text, second_right_diff, diff_list, diff_walker)
                oe_with_diffs += reformated_diff_text
            elif right_diff_type == "=":
                oe_with_diffs += f"[{diff_text},None]"
    oe_with_diffs = reformat_diff_text_from_left(oe_with_diffs)
    oe_with_diffs = reformat_continues_diff(oe_with_diffs)
    oe_with_diffs = rm_punct_note_text(oe_with_diffs)
    return oe_with_diffs


def get_annotated_diffs(reference_edition, witness_edition):
    oe_with_diffs = ""
    normalised_ref_ed = normalise_text(reference_edition)
    normalised_wit_ed = normalise_text(witness_edition)
    diffs = get_diffs(normalised_ref_ed, normalised_wit_ed)
    diffs = list(diffs)
    oe_with_diffs = parse_diffs(diffs)
    oe_with_diffs = oe_with_diffs.replace("#", "\n")
    return oe_with_diffs

def get_base_paths(pecha_base_path):
    base_paths = list(pecha_base_path.iterdir())
    base_paths.sort()
    return base_paths

def get_diff_layer(reference_base_text, witness_base_text):
    diff_layers = {}
    diff_annotated_text = get_annotated_diffs(reference_base_text, witness_base_text)
    diff_layers = parse_diff_layer(diff_annotated_text)
    return diff_layers


def serialize_combined_diff(combined_diff_layer, reference_edition):
    generic_edition = ""
    char_walker = 0
    for _, diff in combined_diff_layer.items():
        diff_start = diff['span']['start']
        diff_end = diff['span']['end']
        elected_diff = diff['elected']
        generic_edition += f"{reference_edition[char_walker:diff_start]}{elected_diff}"
        char_walker = diff_end
    generic_edition += reference_edition[char_walker:]
    return generic_edition


if __name__ == "__main__":
    ref_text = Path('./test/data/opfs/I005/I005.opf/base/v033.txt').read_text(encoding='utf-8')
    # wit_text = Path('./test/data/opfs/I002/I002.opf/base/v033.txt').read_text(encoding='utf-8')
    # ann = get_annotated_diffs(ref_text, wit_text)
    # diff_layer = parse_diff_layer(ann)
    combined_diff = load_yaml(Path('./test/data/result_diff.yaml'))
    # combined_diff = reformat_combined_diff_layer(combined_diff)
    generic = serialize_combined_diff(combined_diff, ref_text)
    Path('./test/data/gen.txt').write_text(generic, encoding='utf-8')
    # ref_text = Path("./test/data/witness_test.txt").read_text(encoding='utf-8')
    # wit_text = Path('./test/data/ref_test.txt').read_text(encoding='utf-8')
    # diff_layers = get_diff_layer(ref_text, wit_text)
    # Path('./test/data/diff_3.txt').write_text(ann, encoding='utf-8')