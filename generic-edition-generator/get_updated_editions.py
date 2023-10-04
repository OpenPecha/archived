import re
from antx import transfer
from openpecha.formatters.hfml import HFMLFormatter

from pathlib import Path
from fix_durchen import fix_end_durchen, fix_start_durchen
from remove_durchen import remove_durchens
from preprocess import remove_durchen_marker

from serialize_hfml import get_hfml_text

def rm_pedurma_header(vol_text):
    vol_text = re.sub("〕\n.*བསྟན་འགྱུར།.+\n", "〕\n", vol_text)
    return vol_text

def transfer_durchen(vol_with_durchen, vol_without_durchen):
    patterns = [
        ["durchen_start", "(<d)"],
        ["durchen_end", "(d>)"]
    ]
    new_vol_text = transfer(vol_with_durchen, patterns, vol_without_durchen)
    return new_vol_text

def get_opf(hfml_path):
    formatter = HFMLFormatter(output_path=Path('./data/opfs/editions_without_durchen/'))
    formatter.create_opf(input_path=hfml_path)

def normalize_durchen(vol_text):
    pub_anns = [
        [r"〈〈?", r"«"],
        [r"〉〉?", r"»"],
        [r"《", r"«"],
        [r"》", r"»"],
        [r"〈〈", r"«"],
        [r"〉〉", r"»"]
    ]
    for old_ann,new_ann in pub_anns: 
        vol_text = re.sub(old_ann, new_ann, vol_text)
    return vol_text


if __name__ == "__main__":
    # pecha_id = "I9B027616"
    # opf_path = Path(f'./data/opfs/editions/{pecha_id}/{pecha_id}.opf')
    # vol_hfmls = get_hfml_text(opf_path)
    # for vol_id, vol_hfml in vol_hfmls.items():
    #     vol_number = int(vol_id[-3:])-845
    #     vol_hfml = re.sub("〕.+", "〕", vol_hfml)
    #     new_hfml = normalize_durchen(vol_hfml)
    #     new_hfml = remove_durchens(new_hfml)
    #     new_hfml = rm_pedurma_header(new_hfml)
    #     new_hfml = remove_durchen_marker(new_hfml)
    #     Path(f'./data/hfmls/editions/{pecha_id}/{vol_id}.txt').write_text(new_hfml, encoding='utf-8')
    hfml_paths = [
        Path('./data/hfmls/editions/I001'),
        Path('./data/hfmls/editions/I002'),
        Path('./data/hfmls/editions/I003'),
    ]
    for hfml_path in hfml_paths:
        vol_paths = list(hfml_path.iterdir())
        for vol_path in vol_paths:
            vol_text = vol_path.read_text(encoding='utf-8')
            new_hfml = normalize_durchen(vol_text)
            new_hfml = remove_durchens(new_hfml)
            new_hfml = rm_pedurma_header(new_hfml)
            new_hfml = remove_durchen_marker(new_hfml)
            vol_text = re.sub("〔.+〕", "", new_hfml)
            vol_text = vol_text.strip()
            Path(f'./data/opfs/editions_without_durchen/{hfml_path.stem}/{hfml_path.stem}.opf/base/{vol_path.stem}.txt').write_text(vol_text, encoding="utf-8")