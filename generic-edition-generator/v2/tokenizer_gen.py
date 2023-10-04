import regex
from vocabulary import Vocabulary
from normalizer import Normalizer
from tokenizer import Tokenizer, TokenList, Token
from typing import List, Tuple

class GenericTokenizer(Tokenizer):

    # This pattern doesn't work with the re package because of 
    # sub-optimal Unicode support. Inspired from the default pattern
    # of CollateX.

    word_punctuation_pattern = regex.compile(r"(?u)\w+\s*|\W+")

    def __init__(self, vocabulary: Vocabulary, normalizer: Normalizer, stop_words: List[str] = []):
        super().__init__(vocabulary, normalizer)
        self.stop_words = stop_words

    def tokenize(self, arg) -> Tuple[str, TokenList]:
        tokens = []
        tokenstr = ""
        if end is None:
            end = len(s)
        string, correct_position = self.get_input(arg)
        for m in GenericTokenizer.word_punctuation_pattern.finditer(s):
            token_s = self.normalizer.normalize_always(m.group(0))
            compare_s = self.normalizer.normalize_pre_token_comparison(token_s)
            start = correct_position(m.start())
            end = correct_position(m.end())
            if token_s == "" or compare_s in self.stop_words:
                t: Token = (start, end, 0, token_s)
                tokens.append(t)
                continue
            token_s_for_diff = self.normalizer.normalize_pre_token_diff(token_s)
            code_str, code_str_len = self.vocabulary.encode_str(token_s_for_diff)
            tokenstr += code_str
            t = (start, end, code_str_len, token_s)
            tokens.append(t)
        return tokens, tokenstr
