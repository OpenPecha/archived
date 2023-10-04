import csv
from pathlib import Path
from tqdm import tqdm

from botok import WordTokenizer, sentence_tokenizer
from openpecha.corpus.download import download_corpus


def _mkdir(path: Path) -> Path:
  path.mkdir(exist_ok=True, parents=True)
  return path

BASE_PATH = Path.home() / ".models"
DATA_PATH = _mkdir(BASE_PATH / "data")

corpus_path = DATA_PATH / "literary_bo"

wt = WordTokenizer()

def sent_tokenize(text):
    tokens = wt.tokenize(text)
    # import pdb; pdb.set_trace()
    sentences = sentence_tokenizer(tokens)
    return [[token.text for token in sentence["tokens"]] for sentence in sentences]
  
def tokenize(text: str):
  sentences = sent_tokenize(text)
  sents_str = ""
  for sentence in sentences:
    # import pdb; pdb.set_trace()
    sents_str += " ".join([token.replace(" ", "_") for token in sentence]) + "\n"
  return sents_str

def get_text_from_tsv_file(fn):
    def handle_punct(token):
        if token:
            if '།' ==  token:
                return token + ' '
            else:
                return token
        else:
            return ' '

    with fn.open() as file:
        tsv_reader = csv.reader(file, delimiter="\t")
        next(tsv_reader, None) # skip header
        tokens = [handle_punct(token) for token, *row in tsv_reader if row]
    text = "".join(tokens)
    text = text.replace(' ། ', ' །')
    text = text.replace('  །', ' །')  
    return text
  
def tokenize_corpus(path, replace=False):
  for pecha_path in tqdm(list(path.iterdir())):
    for fn in pecha_path.iterdir():
      fn_tokenized = fn.parent / f"{fn.stem}.txt"
      if fn.name == "README.md": continue
      if fn_tokenized.is_file() and not replace:
        continue
      print(fn)
      text = get_text_from_tsv_file(fn)
      if not text: continue
      sents_str = tokenize(text)
      fn_tokenized.write_text(sents_str)
    
tokenize_corpus(corpus_path)