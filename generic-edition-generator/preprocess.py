# coding='utf-8'
from pathlib import Path
import re


def remove_durchen_marker(text):
    """
    this cleans up all note markers
    :param text: plain text
    :return: cleaned text
    """

    patterns = [
        # normalize single zeros '༥༥་' --> '༥༥༠
        
        ["༌", "་"],  # normalize NB tsek
        ["([0-9]+?)[ཝ—-]་?([0-9]+)", " <p\g<1>-\g<2>> "],
        ["”", ""],
        ["“", ""],
        ["’", ""],
        ["®", ""],
        ["=", ""],
        ["º", ""],
        ["°", ""],
        ["\*", ""],
        ["\+", ""],
        [":", ""],
        ["-", ""],
        [";", ""],
        ["�", ""],
        ['"', ''],
        ["·",""],
        ["[#€»@\{\$«\!¢\&%\?]", ""],
        ["([①-㊿༠-༩1-9]+)", ""]
    ]

    for p in patterns:
        text = re.sub(p[0], p[1], text)
    
    text = re.sub("<p.+?>", "", text)
    text = re.sub("([aA-zZ]+)", "", text)
    text = re.sub("<r.*?>", "", text)
    text = text.replace("<", "")
    text = text.replace(">", "")

    return text



if __name__ == "__main__":
    pecha_id = "IEA653111"
    base_path = Path(f'./test/opfs/{pecha_id}/{pecha_id}.opf/base/I1PD95878.txt')
    base_text = base_path.read_text(encoding='utf-8')
    clean_base = remove_durchen_marker(base_text)
    base_path.write_text(clean_base, encoding='utf-8')