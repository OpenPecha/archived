from pathlib import Path

from openpecha.utils import load_yaml


def split_work_ids(work_ids):
    counter = 0
    work_id_by_batch = {}
    batch_walker = 1
    cur_batch_work_ids = []

    for work_id in work_ids:
        if counter == 200:
            cur_batch_work_ids.append(work_id)
            work_id_by_batch[batch_walker] = cur_batch_work_ids
            cur_batch_work_ids = []
            counter = 0
            batch_walker += 1
        else:
            cur_batch_work_ids.append(work_id)
            counter += 1
    if cur_batch_work_ids:
        work_id_by_batch[batch_walker] = cur_batch_work_ids
    return work_id_by_batch

def filter_work_without_opf():
    work_id_without_opfs = []
    scan_id_and_pecha_id = load_yaml(Path('./work_id_with_pecha_id.yml'))
    ocred_works = Path('./s3_index/s3_index_20220814.txt').read_text(encoding='utf-8').splitlines()
    for ocred_work in ocred_works:
        if ocred_work in scan_id_and_pecha_id:
            continue
        work_id_without_opfs.append(ocred_work)
    Path('./work_id_without_opf.txt').write_text("\n".join(work_id_without_opfs), encoding='utf-8')

def filter_exception_cases():
    work_logs = Path('./reimport_ocr_done.txt').read_text(encoding='utf-8').splitlines()
    ok_works = []
    for work_log in work_logs:
        work_id = work_log.split(",")[0]
        if "exception" in work_log:
            ok_works.append(work_id)
    ok_works = list(set(ok_works))

    # work_todos = Path('./reimport_ocr_todo.txt').read_text(encoding='utf-8').splitlines()
    # for work in work_todos:
    #     cur_work_id = work.split(",")[0]
    #     if cur_work_id in ok_works:
    #         work_todos.remove(work)
    Path('./reimport_ocr_new_todo.txt').write_text("\n".join(ok_works), encoding='utf-8')


if __name__ == "__main__":
    # work_ids = Path('./work_ids.txt').read_text(encoding='utf-8').splitlines()
    # work_ids = list(set(work_ids))
    # work_ids.sort()
    # work_id_by_batch = split_work_ids(work_ids)
    # for batch_id, batch_work_ids in work_id_by_batch.items():
    #     Path(f'./work_ids_batch_{batch_id}.txt').write_text("\n".join(batch_work_ids), encoding='utf-8')
    # filter_work_without_opf()
    filter_exception_cases()
