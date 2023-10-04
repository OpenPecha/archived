import argparse
import csv
from collections import Counter
from pathlib import Path
from typing import Iterable, List

from tqdm import tqdm

BASE_DIR = Path(__file__).parent.parent
CORPUS_DIR = BASE_DIR / "data" / "corpus"

DICTIONARIES_PATH = BASE_DIR / "data" / "dictionaries"
DICTIONARIES_PATH.mkdir(exist_ok=True)

assert CORPUS_DIR.is_dir()


def get_fns() -> Iterable[Path]:
    return CORPUS_DIR.glob("**/**/*.tsv")


def is_dictionary_candidate(word):
    """word with pos `PUNCT` and `PART` considered not a dict candidate"""
    pos_filter = ["PUNCT", "PART"]
    _, _, pos = word
    if pos in pos_filter:
        return False
    return True


def get_words(fn: Path) -> List[str]:
    with fn.open() as f:
        csv_reader = csv.reader(f, delimiter="\t")
        next(csv_reader)
        for word in csv_reader:
            if not word[0]:
                continue

            if is_dictionary_candidate(word):
                yield word[0]


def save_dictionary(words, output_file):
    with output_file.open("w") as f:
        for word, freq in words:
            f.write(f"{word} {freq}\n")


def build_dictionary(args):
    counter = Counter()

    for fn in tqdm(list(get_fns())):
        words = get_words(fn)
        counter.update(words)

    most_common_words = counter.most_common(args.top)

    output_file = DICTIONARIES_PATH / f"frequency_dictionary_80_literary.txt"
    save_dictionary(most_common_words, output_file)
    print(f"[INFO] dictionary saved at: {output_file}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Unigram Frequency Dictionary")
    parser.add_argument(
        "-t", "--top", type=int, default=80_000, help="Keep only `top` freq words"
    )

    args = parser.parse_args()
    print(args)

    build_dictionary(args)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
