from collections import OrderedDict
from operator import getitem



def find_alt_diff(diff_span, alt_diff_layer):
    for uuid, diff in alt_diff_layer.annotations.items():
        if diff['span'] == diff_span:
            if diff['diff_payload'] == "":
                return "None"
            return diff['diff_payload']
    return None

def has_alt_diffs(diff, alt_diff_layers):
    diff_span = diff['span']
    alt_diffs = {}
        
    for alt_witness_id, alt_diff_layer in alt_diff_layers.items():
        if alt_diff := find_alt_diff(diff_span, alt_diff_layer):
            alt_diff = alt_diff.replace("None", "")
            alt_diffs[alt_witness_id] = alt_diff
        # else:
        #     alt_diffs[alt_witness_id] = diff['src_diff']
    return alt_diffs

def add_missing_diff(diffs, cur_diff, alt_diff_layers):
    alt_witnesses = list(alt_diff_layers.keys())
    for wit_id in alt_witnesses:
        if wit_id in diffs:
            continue
        diffs[wit_id] = cur_diff['src_diff']
    return diffs

def get_elected_diff(diffs, cur_diff, number_of_editions):
    diff_n_count = {}
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
    if elected_diff_count == diff_n_count[cur_diff['src_diff']]:
        elected_diff = cur_diff['src_diff']
    return elected_diff


def combine_diffs(ref_witness_id, witness_id, cur_diff_layer, alt_diff_layers, combined_diffs, number_of_editions):
    
    for uuid, cur_diff in cur_diff_layer.annotations.items():
        diffs = has_alt_diffs(cur_diff, alt_diff_layers)
        if cur_diff['span']['start'] not in combined_diffs:
            diffs[witness_id] = cur_diff['diff_payload']
            diffs[ref_witness_id] = cur_diff['src_diff']
            elected_diff = ''
            combined_diffs[f"{cur_diff['span']['start']}-{cur_diff['span']['end']}"] = {
                'diffs': diffs,
                'elected': elected_diff,
                'span': cur_diff['span'],
                'id': uuid
            }
    return combined_diffs

def reformat_combined_diff_layer(combined_diffs):
    combined_diff_layer = {}
    reformated_combined_diff_layer = {}
    for _, diff in combined_diffs.items():
        reformated_combined_diff_layer[diff['id']] = {
            'span': diff['span'],
            'diffs': diff['diffs'],
            'elected': diff['elected'],
            'start': f"{int(diff['span']['start']):10}-{int(diff['span']['end']):10}"
        }
    sorted_reformated_combined_diff_layer = OrderedDict(sorted(reformated_combined_diff_layer.items(),
       key = lambda x: getitem(x[1], 'start')))
    sorted_reformated_combined_diff_layer = dict(sorted_reformated_combined_diff_layer)
    for cur_diff_id, cur_diff in sorted_reformated_combined_diff_layer.items():
        combined_diff_layer[cur_diff_id] = {
            'span': cur_diff['span'],
            'diffs': cur_diff['diffs'],
            'elected': cur_diff['elected'],
        }
    return combined_diff_layer

def get_alt_diff_layers(witness_id, diff_layers):
    alt_diff_layers = {}
    for cur_witness_id, diff_layer in diff_layers.items():
        if cur_witness_id == witness_id:
            continue
        alt_diff_layers[cur_witness_id] = diff_layer
    return alt_diff_layers


def get_combined_diff_layer(ref_witness_id, diff_layers):
    """ TODO
    If the combine string are too long and start to impact the voting process, at filters before combining
    """
    combined_diffs = {}
    number_of_witness = len(diff_layers)+1
    for witness_id, diff_layer in diff_layers.items():
        alt_diff_layers = get_alt_diff_layers(witness_id, diff_layers)
        combined_diffs = combine_diffs(ref_witness_id, witness_id, diff_layer, alt_diff_layers, combined_diffs,number_of_witness)
    combined_diffs = reformat_combined_diff_layer(combined_diffs)
    return combined_diffs





