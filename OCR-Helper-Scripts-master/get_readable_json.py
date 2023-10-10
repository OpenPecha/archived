import json
import gzip

from pathlib import Path

def read_json(fn):
    with gzip.open(fn, "rb") as f:
        data = json.loads(f.read())
    return data

def convert_json(json_path, output_dir):
    json_content = read_json(json_path)
    output_path = (output_dir / f"{json_path.stem}")
    json_string = json.dumps(json_content, ensure_ascii=False)
    output_path.write_text(json_string, encoding='utf-8')

if __name__ == "__main__":
    output_dir = Path('./data/json/test_re')
    json_paths = list(Path('./data/json/test').iterdir())
    for json_path in json_paths:
        convert_json(json_path, output_dir)