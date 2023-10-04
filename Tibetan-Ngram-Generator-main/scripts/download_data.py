from pathlib import Path

from openpecha.corpus.download import download_corpus

BASE_DIR = Path(__file__).parent.parent
output_path = BASE_DIR / "data"
download_corpus("literary_bo", output_path=output_path)
