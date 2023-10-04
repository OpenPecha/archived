import re
from pathlib import Path

from pedurma.texts import get_pages

def update_durchen_start(page):
    new_pg = ""
    if "བསྡུར་མཆ" in page:
        page = page.replace("<d", "")
        lines = page.splitlines()
        for line in lines:
            if "བསྡུར་མཆ" in line:
                new_pg += f"<d{line}\n"
            else:
                new_pg += f"{line}\n"
    else:
        new_pg = page
    return new_pg

def update_durchen_end(new_vol_text, prev_page, page):
    page = page.replace("d>", "")
    if "༄༅" in page:
        new_prev_page = prev_page + "d>\n"
        new_vol_text = new_vol_text.replace(prev_page, new_prev_page)
        new_vol_text += page
    else:
        new_vol_text += f"{page}d>\n"
    return new_vol_text
        
def fix_start_durchen(vol_text):
    new_vol_text = ""
    pages = get_pages(vol_text)
    for page in pages:
        if "<d" in page:
            page = update_durchen_start(page)
        new_vol_text += f"{page}"
    return new_vol_text

def fix_end_durchen(vol_text):
    new_vol_text = ""
    pages = get_pages(vol_text)
    prev_page = pages[0]
    for page in pages:
        if "d>" in page:
            new_vol_text = update_durchen_end(new_vol_text, prev_page, page)
        else:
            new_vol_text += f"{page}"
        prev_page = page
    return new_vol_text


if __name__ == "__main__":
    vol_text = Path('./data/hfmls/editions/T001/I1PD95846.txt').read_text(encoding='utf-8')
    new_vol_text = fix_start_durchen(vol_text)
    new_vol_text = fix_end_durchen(new_vol_text)
    Path('./data/hfmls/editions/T001/update_durchen.txt').write_text(new_vol_text, encoding='utf-8')