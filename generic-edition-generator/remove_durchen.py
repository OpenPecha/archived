import re
from pathlib import Path


from pedurma.texts import get_pages

from fix_durchen import fix_start_durchen

def is_durchen_page(page):
    if "«" in page and "»" in page:
        return True
    elif "བསྡུར་འབྲས་" in page:
        return True
    return False

# def remove_durchens(vol_text):
#     new_vol_text = ""
#     pages = get_pages(vol_text)
#     durchen_start = False
#     for page in pages:
#         if "<d" in page:
#             page = page.replace("\n", "𰵀")
#             new_pg = re.sub("(.+)<d.+", "\g<1>\n", page)
#             new_pg = new_pg.replace("𰵀", "\n")
#             new_vol_text += new_pg
#             if not re.search("<d.+?d>", page):
#                 durchen_start = True
#         elif durchen_start:
#             if "d>" in page:
#                 durchen_start = False
#         else:
#             new_vol_text += page
#     return new_vol_text

def remove_durchens(vol_text):
    pages = get_pages(vol_text)
    new_vol_text = ""
    for page in pages:
        if is_durchen_page(page):
            if "བསྡུར་མཆན" in page:
                page = page.replace("\n", "𰵀")
                page = re.sub("(.+)བསྡུར་མཆན.+", r"\g<1>", page)
                page = page.replace("𰵀", "\n")
                new_vol_text += page +"\n"
        else:
            new_vol_text += page
    return new_vol_text

if __name__ == "__main__":
    vol_paths = list(Path('./data/hfmls/tengyur_with_durchen').iterdir())
    for vol_path in vol_paths:
        vol_text = vol_path.read_text(encoding='utf-8')
        vol_text = fix_start_durchen(vol_text)
        vol_text_without_durchen = remove_durchens(vol_text)
        Path(f'./data/hfmls/editions/tengyur_without_durchen/{vol_path.stem}.txt').write_text(vol_text_without_durchen, encoding="utf-8")

 
