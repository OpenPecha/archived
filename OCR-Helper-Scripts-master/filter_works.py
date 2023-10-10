from pathlib import Path

def get_work_id(log_line):
    log_info = log_line.split(" ")
    try:
        return log_info[3]
    except:
        print(log_line)
        return ""


def filter_work_with_issue(batch_works, log):
    log_lines = log.splitlines()
    work_with_issue = []
    for log_line in log_lines:
        work_with_issue.append(get_work_id(log_line))
    for work_id in batch_works:
        if work_id in work_with_issue:
            batch_works.remove(work_id)
    return batch_works

if __name__ == "__main__":
    batch_works = Path('./work_ids_batch_1.txt').read_text(encoding='utf-8') + "\n"
    batch_works += Path('./work_ids_batch_2.txt').read_text(encoding='utf-8') + "\n"
    batch_works += Path('./work_ids_batch_3.txt').read_text(encoding='utf-8') + "\n"
    batch_works += Path('./work_ids_batch_4.txt').read_text(encoding='utf-8') + "\n"
    batch_works += Path('./work_ids_batch_5.txt').read_text(encoding='utf-8') + "\n"
    logs = Path('./s3_download_issue/s3_download_issue_batch_1.log').read_text(encoding='utf-8') + "\n"
    logs += Path('./s3_download_issue/s3_download_issue_batch_2.log').read_text(encoding='utf-8') + "\n"
    logs += Path('./s3_download_issue/s3_download_issue_batch_3.log').read_text(encoding='utf-8') + "\n"
    logs += Path('./s3_download_issue/s3_download_issue_batch_4.log').read_text(encoding='utf-8') + "\n"
    logs += Path('./s3_download_issue/s3_download_issue_batch_5.log').read_text(encoding='utf-8') + "\n"
    batch_works = batch_works.splitlines()
    batch_works = list(set(batch_works))
    batch_works.sort()
    valid_works = filter_work_with_issue(batch_works, logs)
    Path('./Valid_works.txt').write_text("\n".join(valid_works), encoding='utf-8')


