import shutil
from pathlib import Path
from openpecha.utils import load_yaml, dump_yaml

def rm_base(opf_path, non_derge_vols):
    base_paths = list((opf_path/ "base").iterdir())
    for base_path in base_paths:
        vol_num = int(base_path.stem[-3:])-845
        if str(vol_num) in non_derge_vols:
            img_grp_id = f"I1PD9{vol_num+5845}"
            base_path.rename(Path(base_path.parent, f"{img_grp_id}.txt"))
        else:
            base_path.unlink()

def rm_layers(opf_path, non_derge_vols):
    layer_paths = list((opf_path/ "layers").iterdir())
    for layer_path in layer_paths:
        vol_num = int(layer_path.stem[-3:])-845
        if str(vol_num) in non_derge_vols:
            img_grp_id = f"I1PD9{vol_num+5845}"
            newname = layer_path.parent / img_grp_id
            newname.parent.mkdir(parents=True, exist_ok=True)
            layer_path.rename(newname)
        else:
            shutil.rmtree(layer_path)

def update_meta(opf_path):
    (opf_path / "meta.yml").unlink()
    meta = load_yaml(Path('./data/opfs/editions/I4DBEE949/I4DBEE949.opf/meta.yml'))
    meta['id'] = opf_path.stem
    dump_yaml(meta, (opf_path / "meta.yml"))

def remove_derge_vol(opf_path, non_derge_vols):
    rm_base(opf_path, non_derge_vols)
    rm_layers(opf_path, non_derge_vols)
    update_meta(opf_path)


if __name__ == "__main__":
    non_derge_vols = Path('./non_derge_vols.txt').read_text(encoding='utf-8').splitlines()
    opf_path = Path('./data/opfs/editions/IA3E40644/IA3E40644.opf')
    remove_derge_vol(opf_path, non_derge_vols)