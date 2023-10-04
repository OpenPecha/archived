import csv
from pathlib import Path

from botok import BoString
from botok.vars import CharMarkers
from tqdm import tqdm

BASE_DIR = Path(__file__).parent.parent
CORPUS_DIR = BASE_DIR / "data" / "corpus"

def get_tokens(fn):
    with fn.open() as file:
        tsv_reader = csv.reader(file, delimiter="\t")
        next(tsv_reader, None) # skip header
        for token, *row in tsv_reader:
            if not token: continue
            yield token

def is_punt(string):
    normal_punt = CharMarkers(5)
    special_punt = CharMarkers(6)
    bo_string = BoString(string)
    for _, char_marker_value in bo_string.base_structure.items():
        char_maker = CharMarkers(char_marker_value)
        if char_maker == normal_punt or char_maker == special_punt:
            return True
    return False

def tokenize_sents(tokens: str) ->  str:
    sents_str = ""
    sent_tokens = []
    for token in tokens:
        if is_punt(token):
            if sent_tokens:
                sent_str = " ".join(sent_tokens)
                sents_str += sent_str + "\n"
                sent_tokens = []
            continue

        sent_tokens.append(token)

    if sent_tokens:
        sent_str = " ".join(sent_tokens)
        sents_str += sent_str + "\n"

    return sents_str


def tokenize_corpus(path, replace=False):
  for pecha_path in tqdm(list(path.iterdir())):
    for fn in pecha_path.iterdir():
      fn_tokenized = fn.parent / f"{fn.stem}.txt"
      if not fn.name.endswith(".tsv"): continue
      if fn_tokenized.is_file() and not replace:
        continue
      tokens = get_tokens(fn)
      sents_str = tokenize_sents(tokens)
      fn_tokenized.write_text(sents_str)


def main():
    for corpus_path in CORPUS_DIR.iterdir():
        tokenize_corpus(corpus_path, replace=True)


if __name__ == "__main__":
    main()
