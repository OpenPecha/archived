from pathlib import Path

from pedurma.notes import get_durchen_pages

from preprocess import preprocess_namsel_body

def remove_pedurma_note_marker(vol_text):
    new_vol_text = ""
    pages = get_durchen_pages(vol_text)
    for pg_id, page in pages.items():
        new_vol_text += f"{pg_id}{preprocess_namsel_body(page)}\n"
    return new_vol_text

if __name__ == "__main__":
    vol_text = Path('./data/hfmls/editions/T003/v001.txt').read_text(encoding='utf-8')
    vol_text_with_marker = remove_pedurma_note_marker(vol_text)
    Path('./data/I1PD95848.txt').write_text(vol_text_with_marker, encoding='utf-8')

