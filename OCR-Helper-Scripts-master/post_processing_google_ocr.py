import gzip
import json
import logging

from pathlib import Path
from antx import transfer

logging.basicConfig(filename="postprocessing_issue.log", level=logging.DEBUG, filemode="w")

def read_json(fn):
    with gzip.open(fn, "rb") as f:
        data = json.loads(f.read())
    return data

def get_bounding_poly_mid(bounding_poly):
    """Calculate middle of the bounding poly vertically using y coordinates of the bounding poly

    Args:
        bounding_poly (dict): bounding poly's details

    Returns:
        float: mid point's y coordinate of bounding poly
    """
    y1 = bounding_poly["boundingBox"]["vertices"][0].get('y', 0)
    y2 = bounding_poly["boundingBox"]["vertices"][2].get('y', 0)
    y_avg = (y1 + y2) / 2
    return y_avg

def get_avg_bounding_poly_height(bounding_polys):
    """Calculate the average height of bounding polys in page

    Args:
        bounding_polys (list): list of boundingBoxs

    Returns:
        float: average height of bounding ploys
    """
    height_sum = 0
    for bounding_poly in bounding_polys:
        y1 = bounding_poly["boundingBox"]["vertices"][0].get('y', 0)
        y2 = bounding_poly["boundingBox"]["vertices"][2].get('y', 0)
        height_sum += y2 - y1
    avg_height = height_sum / len(bounding_polys)
    return avg_height

def is_in_cur_line(prev_bounding_poly, bounding_poly, avg_height):
    """Check if bounding poly is in same line as previous bounding poly
    a threshold to check the conditions set to 10 but it can varies for pecha to pecha

    Args:
        prev_bounding_poly (dict): previous bounding poly
        bounding_poly (dict): current bounding poly
        avg_height (float): average height of all the bounding polys in page

    Returns:
        boolean: true if bouding poly is in same line as previous bounding poly else false
    """
    threshold = 10
    if get_bounding_poly_mid(bounding_poly)- get_bounding_poly_mid(prev_bounding_poly)< avg_height/threshold:
        return True
    else:
        return False

def get_low_confidence_ann(bounding_poly):
    if bounding_poly['confidence'] >0.9:
        return bounding_poly['text']
    else:
        return f"ר{bounding_poly['text']}ר"

def get_lines(bounding_polys):
    prev_bounding_poly = bounding_polys[0]
    lines = []
    lines_with_ann = []
    cur_line = ''
    cur_line_with_ann = ''
    avg_line_height = get_avg_bounding_poly_height(bounding_polys)
    for bounding_poly in bounding_polys:
        if is_in_cur_line(prev_bounding_poly, bounding_poly, avg_line_height):
            cur_line += bounding_poly.get("text", "")
            cur_line_with_ann += get_low_confidence_ann(bounding_poly)
        else:
            lines.append(cur_line)
            lines_with_ann.append(cur_line_with_ann)
            cur_line = bounding_poly.get("text", "")
            cur_line_with_ann = get_low_confidence_ann(bounding_poly)
        prev_bounding_poly = bounding_poly
    if cur_line:
        lines.append(cur_line)
    if cur_line_with_ann:
        lines_with_ann.append(cur_line_with_ann)
    return lines, lines_with_ann

def get_height_range(avg_box_height, bounding_polys):
    height_diffs = []
    for bounding_poly in bounding_polys:
        y1 = bounding_poly["boundingBox"]["vertices"][0].get('y', 0)
        y2 = bounding_poly["boundingBox"]["vertices"][2].get('y', 0)
        height = y2-y1
        height_diffs.append(int(avg_box_height-height))
    avg_diff = sum(height_diffs) // len(height_diffs)
    lower_bound_height = int(avg_box_height - avg_diff)
    upper_bound_height = int(avg_box_height+avg_diff)
    return lower_bound_height, upper_bound_height

def filter_bounding_polys(bounding_polys):
    main_region_bounding_polys = []
    noise_bounding_polys = []
    avg_box_height = get_avg_bounding_poly_height(bounding_polys)
    lower_bound_height, upper_bound_height = get_height_range(avg_box_height, bounding_polys)
    for bounding_poly in bounding_polys:
        y1 = bounding_poly["boundingBox"]["vertices"][0].get('y', 0)
        y2 = bounding_poly["boundingBox"]["vertices"][2].get('y', 0)
        height = y2-y1
        if height >= lower_bound_height:
            main_region_bounding_polys.append(bounding_poly)
        else:
            noise_bounding_polys.append(bounding_poly)
    return main_region_bounding_polys, noise_bounding_polys

def find_centriod(bounding_poly):
    sum_of_x = 0
    sum_of_y = 0
    for vertice in bounding_poly["boundingBox"]["vertices"]:
        sum_of_x += vertice['x']
        sum_of_y += vertice['y']
    centriod = [sum_of_x/4, sum_of_y/4]
    return centriod

def get_poly_sorted_on_y(bounding_poly_centriods):
    sorted_on_y_polys = sorted(bounding_poly_centriods , key=lambda k: [k[1]])
    return sorted_on_y_polys

def get_poly_sorted_on_x(sorted_on_y_polys, avg_box_height):
    prev_bounding_poly = sorted_on_y_polys[0]
    lines = []
    cur_line = []
    sorted_polys = []
    for bounding_poly in sorted_on_y_polys:
        if abs(bounding_poly[1]-prev_bounding_poly[1]) < avg_box_height/10:
            cur_line.append(bounding_poly)
        else:
            lines.append(cur_line)
            cur_line = []
            cur_line.append(bounding_poly)
        prev_bounding_poly = bounding_poly
    if cur_line:
        lines.append(cur_line)
    for line in lines:
        sorted_line = sorted(line, key=lambda k: [k[0]])
        for poly in sorted_line:
            sorted_polys.append(poly)
    return sorted_polys

def sort_bounding_polys(main_region_bounding_polys):
    bounding_polys = {}
    bounding_poly_centriods = []
    avg_box_height = get_avg_bounding_poly_height(main_region_bounding_polys)
    for bounding_poly in main_region_bounding_polys:
        centroid = find_centriod(bounding_poly)
        bounding_polys[f"{centroid[0]},{centroid[1]}"] = bounding_poly
        bounding_poly_centriods.append(centroid)
    sorted_bounding_polys = []
    sort_on_y_polys = get_poly_sorted_on_y(bounding_poly_centriods)
    sorted_bounding_poly_centriods = get_poly_sorted_on_x(sort_on_y_polys, avg_box_height)
    for bounding_poly_centriod in sorted_bounding_poly_centriods:
        sorted_bounding_polys.append(bounding_polys[f"{bounding_poly_centriod[0]},{bounding_poly_centriod[1]}"])
    return sorted_bounding_polys

def get_char_base_bounding_polys(response):
    bounding_polys = []
    cur_word = ""
    for page in response['fullTextAnnotation']['pages']:
        for block in page['blocks']:
            for paragraph in block['paragraphs']:
                for word in paragraph['words']:
                    for symbol in word['symbols']:
                        cur_word += symbol['text']
                    word['text'] = cur_word
                    cur_word = ""
                    bounding_polys.append(word)
    return bounding_polys

def get_page_content(page):
    """parse page response to generate page content by reordering the bounding polys

    Args:
        page (dict): page content response given by google ocr engine

    Returns:
        str: page content
    """
    postprocessed_page_content =''
    try:
        page_content = page['textAnnotations'][0]['description']
    except:
        postprocessed_page_content += '---------\n'
        return postprocessed_page_content, postprocessed_page_content
    char_base_bounding_polys = get_char_base_bounding_polys(page)
    # bounding_polys = page['textAnnotations'][1:]
    # main_region_bounding_polys, noise_bounding_polys = filter_bounding_polys(bounding_polys)
    # sorted_main_region_bounding_polys = sort_bounding_polys(main_region_bounding_polys)
    # if sorted_main_region_bounding_polys:
    #     lines = get_lines(sorted_main_region_bounding_polys)
    # else:
    sorted_bounding_polys = sort_bounding_polys(char_base_bounding_polys)
    lines, lines_with_ann = get_lines(sorted_bounding_polys)
    page_content_without_space = "\n".join(lines)
    page_with_ann = "\n".join(lines_with_ann)
    postprocessed_page_content = transfer_space(page_content, page_content_without_space)
    page_with_ann = transfer_space(page_content, page_with_ann)
    return postprocessed_page_content, page_content

def get_vol_content(vol_path):
    vol_content = ''
    vol_without_post = ""
    page_paths = list(vol_path.iterdir())
    page_paths.sort()
    for pg_num, page_path in enumerate(page_paths,1):
        page = read_json(page_path)
        if page:
            post_page, pg_content = get_page_content(page)
            vol_content += f'{post_page}\n\n'
            vol_without_post += f'{pg_content}\n\n'
        logging.info(f'{page_path} completed..')
    return vol_content, vol_without_post

def transfer_space(base_with_space, base_without_space):
    """transfer space from base with space to without space

    Args:
        base_with_space (str): base with space which is extracted from page['textAnnotations'][0]['description']
        base_without_space (str): base without space as it is generated using accumulating non space bounding_poly only

    Returns:
        [str]: page content
    """
    new_base = transfer(
        base_with_space,[
        ["space",r"( )"],
        ],
        base_without_space,
        output="txt",
    )
    return new_base

def is_pering(main_box):
    x1 = main_box["boundingPoly"]["vertices"][0]["x"]
    x2 = main_box["boundingPoly"]["vertices"][1]["x"]
    y1 = main_box["boundingPoly"]["vertices"][0]["y"]
    y2 = main_box["boundingPoly"]["vertices"][4]["y"]
    length = x2-x1
    width = y2-y1
    if length > width:
        return True
    else:
        return False

def process_pecha(pecha_path, output_path):
    vol_paths = list(Path(pecha_path).iterdir())
    vol_paths.sort()
    for vol_path in vol_paths:
        vol_content, vol_without_post = get_vol_content(vol_path)
        (Path(output_path) / f'{vol_path.stem}.txt').write_text(vol_content, encoding='utf-8')
        (Path(output_path) / f'{vol_path.stem}_without_post.txt').write_text(vol_without_post, encoding='utf-8')
        print(f'{vol_path.stem} completed...')

if __name__ == "__main__":
    pecha_path = './data/json/I0001'
    output_path = './data/text/I0001'
    process_pecha(pecha_path, output_path)