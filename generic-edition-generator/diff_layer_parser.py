import re
import json

from enum import Enum

from openpecha.core.layer import Layer, LayerEnum
from openpecha.core.annotations import BaseAnnotation, Span
from openpecha.utils import dump_yaml

from pathlib import Path

extended_LayerEnum = [(l.name, l.value) for l in LayerEnum] + [("diff", "Diff"), ("generic_diff", "Generic_diff")]
LayerEnum = Enum("LayerEnum", extended_LayerEnum)

class ExtentedLayer(Layer):
    annotation_type: LayerEnum
class Diff(BaseAnnotation):
    src_diff: str
    diff_payload: str

class GenericDiff(BaseAnnotation):
    diffs: dict
    elected: str

def get_chunks(oe_with_diffs):
    chunks = []
    cur_chunk = ""
    text_parts = re.split("(\[.+?,.+?\])", oe_with_diffs)
    for text_part in text_parts:
        if re.search("\[.+?,.+?\]", text_part):
            cur_chunk += text_part
            chunks.append(cur_chunk)
            cur_chunk = ""
        else:
            cur_chunk += text_part
    return chunks

def parse_diff_anns(chunk, char_walker):
    diff_ann = re.search("\[(.+?),(.+?)\]", chunk)
    src_txt = diff_ann.group(1)
    src_txt = src_txt.replace("#", "\n")
    src_txt = src_txt.replace("None", "")
    diff_payload = diff_ann.group(2)
    diff_payload = diff_payload.replace("#", "\n")
    diff_payload = diff_payload.replace("None","")
    ann_start = diff_ann.start() + char_walker
    ann_end = ann_start + len(src_txt)
    span = Span(start=ann_start, end=ann_end)
    diff_ann = Diff(span=span, src_diff=src_txt, diff_payload=diff_payload)
    return diff_ann

def parse_diff_layer(oe_with_diffs):
    char_walker = 0
    diff_layer = ExtentedLayer(annotation_type=LayerEnum.diff)
    
    oe_with_diffs = oe_with_diffs.replace("\n","#")
    chunks = get_chunks(oe_with_diffs)
    for chunk in chunks:
        diff_layer.set_annotation(parse_diff_anns(chunk, char_walker))
        chunk_without_ann = re.sub("\[(.+?),.+?\]", "\g<1>", chunk)
        char_walker += len(chunk_without_ann)
    return diff_layer  
 
if __name__ == "__main__":
    diff_an = Path('./test/data/diff_ann_3.txt').read_text(encoding='utf-8')
    layer = parse_diff_layer(diff_an)