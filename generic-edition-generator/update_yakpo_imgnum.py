from pathlib import Path


from openpecha.utils import load_yaml, dump_yaml


def update_pagination(pagination):
    for uuid, pg_ann in pagination['annotations'].items():
        img_num = int(pg_ann['reference'][-4:])
        pagination['annotations'][uuid]['imgnum'] = img_num
    return pagination

if __name__ == '__main__':
    pagination_layer_paths = list(Path('./data/opfs/editions/PC445E4EA/PC445E4EA.opf/layers').iterdir())
    pagination_layer_paths.sort()
    for pagination_layer_path in pagination_layer_paths:
        old_pagination = load_yaml((pagination_layer_path / 'Pagination.yml'))
        new_pagination = update_pagination(old_pagination)
        dump_yaml(new_pagination, (pagination_layer_path / 'Pagination.yml'))