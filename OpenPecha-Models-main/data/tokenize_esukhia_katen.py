from pathlib import Path

from tqdm import tqdm
from botok import WordTokenizer, sentence_tokenizer

BASE_PATH = Path.home() / ".models"
DATA_PATH = BASE_PATH / "data"

corpus_path = DATA_PATH / "esukhia_katen"
assert corpus_path.is_dir()

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

def tokenize_corpus(path, replace=False):
  for pecha_path in tqdm(list(path.iterdir())):
    for fn in pecha_path.iterdir():
      fn_tokenized = fn.parent / f"{fn.stem}-tokenized.txt"
      if fn_tokenized.is_file() and not replace:
        continue
      text = fn.read_text()
      if not text: continue
      sents_str = tokenize(text)
      fn_tokenized.write_text(sents_str)
      
tokenize_corpus(corpus_path)