import gzip
import json
import logging

from pathlib import Path

from matplotlib.pyplot import polar
# from antx import transfer

logging.basicConfig(filename="postprocessing_issue.log", level=logging.DEBUG, filemode="w")

class BBox:
    def __init__(self, text: str, vertices: list, confidence: float, language: str):

        self.text = text
        self.vertices = vertices
        self.confidence = confidence
        self.language = language
    

    
    def get_box_height(self):
        y1 = self.vertices[0][1]
        y2 = self.vertices[1][1]
        height = abs(y2-y1)
        return height
    
    
    def get_box_orientation(self):
        x1= self.vertices[0][0]
        x2 = self.vertices[1][0]
        y1= self.vertices[0][1]
        y2 = self.vertices[1][1]
        width = abs(x2-x1)
        length = abs(y2-y1)
        if width > length:
            return "landscape"
        else:
            return "portrait"


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
    y1 = bounding_poly.vertices[0][1]
    y2 = bounding_poly.vertices[2][1]
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
        y1 = bounding_poly.vertices[0][1]
        y2 = bounding_poly.vertices[2][1]
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

def get_lines(bounding_polys):
    prev_bounding_poly = bounding_polys[0]
    lines = []
    cur_line = ''
    avg_line_height = get_avg_bounding_poly_height(bounding_polys)
    for bounding_poly in bounding_polys:
        if is_in_cur_line(prev_bounding_poly, bounding_poly, avg_line_height):
            cur_line += bounding_poly.text
        else:
            lines.append(cur_line)
            cur_line = bounding_poly.text
        prev_bounding_poly = bounding_poly
    if cur_line:
        lines.append(cur_line)
    return lines

def get_height_range(avg_box_height, bounding_polys):
    height_diffs = []
    for bounding_poly in bounding_polys:
        y1 = bounding_poly["boundingBox"]["vertices"][0].get('y', 0)
        y2 = bounding_poly["boundingBox"]["vertices"][2].get('y', 0)
        height = y2-y1
        height_diffs.append(abs(avg_box_height-height))
    avg_diff = sum(height_diffs) // len(height_diffs)
    lower_bound_height = abs(avg_box_height - avg_diff)
    upper_bound_height = avg_box_height+avg_diff
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
        if height >= lower_bound_height and height <= upper_bound_height:
            main_region_bounding_polys.append(bounding_poly)
        else:
            noise_bounding_polys.append(bounding_poly)
    return main_region_bounding_polys, noise_bounding_polys

def find_centriod(bounding_poly):
    sum_of_x = 0
    sum_of_y = 0
    for vertice in bounding_poly.vertices:
        sum_of_x += vertice[0]
        sum_of_y += vertice[1]
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

def get_language_code(bounding_poly):
    properties = bounding_poly.get("property", {})
    if properties:
        languages = properties.get("detectedLanguages", [])
        if languages:
            return languages[0]
    return ""

def extract_vertices(word):
    vertices = []
    for vertice in word['boundingBox']['vertices']:
        vertices.append([vertice['x'], vertice['y']])
    return vertices

def dict_to_bbox(word):
    text = word.get('text', '')
    confidence = word.get('confidence', 0.0)
    language = get_language_code(word)
    vertices = extract_vertices(word)
    bbox = BBox(text=text, vertices=vertices, confidence=confidence, language=language)
    return bbox

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
                    bbox = dict_to_bbox(word)
                    bounding_polys.append(bbox)
    return bounding_polys

def get_avg_char_width(response):
    widths = []
    for page in response['fullTextAnnotation']['pages']:
        for block in page['blocks']:
            for paragraph in block['paragraphs']:
                for word in paragraph['words']:
                    for symbol in word['symbols']:
                        vertices = symbol['boundingBox']['vertices']
                        x1 = vertices[0]['x']
                        x2 = vertices[1]['x']
                        width = x2-x1
                        widths.append(width)
    return sum(widths) / len(widths)

def get_space_poly_vertices(cur_bounding_poly, next_poly):
    vertices = [
        cur_bounding_poly.vertices[1],
        next_poly.vertices[0],
        next_poly.vertices[3],
        cur_bounding_poly.vertices[2],
    ]
    return vertices

def has_space_after(cur_bounding_poly, next_poly, avg_char_width):
    cur_poly_top_right_corner = cur_bounding_poly.vertices[1][0]
    next_poly_top_left_corner = next_poly.vertices[0][0]
    if next_poly_top_left_corner - cur_poly_top_right_corner > avg_char_width:
        space_poly_vertices = get_space_poly_vertices(cur_bounding_poly, next_poly)
        space_box = BBox(
            text=" ",
            vertices=space_poly_vertices,
            confidence=1.0,
            language="bo"
        )
        return space_box
    return None

def insert_space_bounding_poly(bounding_polys, avg_char_width):
    new_bounding_polys = []
    for poly_walker, cur_bounding_poly in enumerate(bounding_polys):
        if poly_walker == len(bounding_polys)-1:
            new_bounding_polys.append(cur_bounding_poly)
        else:
            next_poly = bounding_polys[poly_walker+1]
            if space_poly := has_space_after(cur_bounding_poly, next_poly, avg_char_width):
                new_bounding_polys.append(cur_bounding_poly)
                new_bounding_polys.append(space_poly)
            else:
                new_bounding_polys.append(cur_bounding_poly)
    return new_bounding_polys

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
    avg_char_width = get_avg_char_width(page)
    char_base_bounding_polys = get_char_base_bounding_polys(page)
    # bounding_polys = page['textAnnotations'][1:]
    # main_region_bounding_polys, noise_bounding_polys = filter_bounding_polys(bounding_polys)
    # sorted_main_region_bounding_polys = sort_bounding_polys(main_region_bounding_polys)
    # if sorted_main_region_bounding_polys:
    #     lines = get_lines(sorted_main_region_bounding_polys)
    # else:
    sorted_bounding_polys = sort_bounding_polys(char_base_bounding_polys)
    sorted_bounding_polys = insert_space_bounding_poly(sorted_bounding_polys, avg_char_width)
    lines = get_lines(sorted_bounding_polys)
    page_content_without_space = "\n".join(lines)
    postprocessed_page_content = "\n".join(lines) 
    # postprocessed_page_content = transfer_space(page_content, page_content_without_space)
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
    pecha_path = './data/json/P000009'
    output_path = './data/text/P000009'
    process_pecha(pecha_path, output_path)