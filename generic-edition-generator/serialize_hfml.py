import re
from pathlib import Path
from openpecha.serializers.hfml import HFMLSerializer

def get_hfml_text(opf_path):
    """Return hmfl of text from the pecha opf

    Args:
        opf_path (str): opf path
        index (dict, optional): pecha index. Defaults to None.

    Returns:
        dict: vol id as key and hfml as the content
    """
    serializer = HFMLSerializer(opf_path, layers=["Pagination", "Durchen"])
    serializer.apply_layers()
    hfml_text = serializer.get_result()
    return hfml_text


if __name__ == "__main__":
    pecha_id = "187ed94f85154ea5b1ac374a651e1770"
    opf_path = Path(f'./data/opfs/collection_opf/{pecha_id}/{pecha_id}.opf')
    hfmls = get_hfml_text(opf_path)
    for vol, hfml in hfmls.items():
        hfml = re.sub(r"[𰵀-󴉱]", "", hfml)
        Path(f'./data/hfmls/namsel_tengyur_with_durchen/{vol}.txt').write_text(hfml, encoding='utf-8')