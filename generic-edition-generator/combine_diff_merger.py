from pathlib import Path
from openpecha.utils import load_yaml, dump_yaml


def is_overlapping(diff, prev_diff):
    if diff != prev_diff and diff['span']['start'] < prev_diff['span']['end']:
        return True
    return False

def is_sub_set(diff, prev_diff):
    if diff == prev_diff:
        return False
    elif prev_diff['span']['start'] < diff['span']['start'] and prev_diff['span']['end'] > diff['span']['end']:
        return True
    else:
        False

def fill_overflow(diff, prev_diff, left_over_flow, right_over_flow):
    diff_payloads = {}
    for wit_id, diff_payload in diff['diffs'].items():
        diff_payloads[wit_id] = f"{left_over_flow}{diff_payload}"
    for wit_id, diff_payload in prev_diff['diffs'].items():
        diff_payloads[wit_id] = f"{diff_payload}{right_over_flow}"
    diff['diffs']= diff_payloads
    return diff

def get_left_overflow(diff, prev_diff, ref_wit_id):
    left_offset = diff['span']['start'] - prev_diff['span']['start']
    left_over_flow = ""
    if left_offset > 0:
        left_over_flow = prev_diff['diffs'][ref_wit_id][:left_offset]
    return left_offset, left_over_flow

def get_right_overflow(diff, prev_diff, ref_wit_id):
    right_offset = diff['span']['end'] - prev_diff['span']['end']
    right_over_flow = ""
    if right_offset>0:
        right_over_flow = diff['diffs'][ref_wit_id][-right_offset:]
    return right_offset, right_over_flow

def update_diff_span(diff, left_offset):
    diff['span']['start'] -= left_offset
    return diff

def merge_prev_diff(diff, prev_diff, ref_wit_id, is_sub_set):
    left_offset, left_over_flow = get_left_overflow(diff, prev_diff, ref_wit_id)
    right_offset,right_over_flow = get_right_overflow(diff, prev_diff, ref_wit_id)
    diff = fill_overflow(diff, prev_diff, left_over_flow, right_over_flow)
    if not is_sub_set:
        diff = update_diff_span(diff, left_offset)
    else:
        diff['span'] = prev_diff['span']
    diff['elected'] = get_elected_diff(diff['diffs'], ref_wit_id)
    return diff



def merge_combine_diff(combine_diff, ref_wit_id):
    reformated_combine_diffs = {}
    prev_diff_id = list(combine_diff.keys())[0]
    for diff_id, diff in combine_diff.items():
        prev_diff = combine_diff[prev_diff_id]
        if is_overlapping(diff, prev_diff):
            is_sub_set_flag = is_sub_set(diff, prev_diff)
            reformated_combine_diffs[diff_id] = merge_prev_diff(diff, prev_diff, ref_wit_id, is_sub_set_flag)
            del reformated_combine_diffs[prev_diff_id]
        else:
            diff['elected'] = get_elected_diff(diff['diffs'], ref_wit_id)
            reformated_combine_diffs[diff_id] = diff
        prev_diff_id = diff_id
    return reformated_combine_diffs


def get_elected_diff(diffs, ref_wit_id):
    diff_n_count = {}
    ref_diff = diffs[ref_wit_id]
    elected_diff = ""
    elected_diff_count = 0
    diff_texts = list(diffs.values())
    unique_diffs = list(set(diff_texts))
    for unique_diff in unique_diffs:
        diff_n_count[unique_diff] = diff_texts.count(unique_diff)
    for diff, count in diff_n_count.items():
        if count > elected_diff_count:
            elected_diff = diff
            elected_diff_count = count
    if elected_diff_count == diff_n_count[ref_diff]:
        elected_diff = ref_diff
    return elected_diff

if __name__ == "__main__":
    combine_diff = load_yaml(Path('./test/data/combined_diff.yaml'))
    diffs = merge_combine_diff(combine_diff, ref_wit_id="I005")
    dump_yaml(diffs,Path('./test/data/result_diff.yml'))

