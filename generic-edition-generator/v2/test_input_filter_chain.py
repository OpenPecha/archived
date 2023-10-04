from input_filter import InputFilter
from input_filter_position import PositionInputFilter
from input_filter_pattern import PatternInputFilter
import re
import bisect

def test_bisect():
    t = [5, 10]
    assert(bisect.bisect(t, 7) == 1)
    assert(bisect.bisect(t, 2) == 0)
    assert(bisect.bisect(t, 12) == 2)
    assert(bisect.bisect(t, 10) == 2)

def test_position_simple():
    input_str = "aabbbbcc"
    filtered = PositionInputFilter(input_str, 3)
    s = filtered.get_string()
    assert(s == "bbbcc")
    assert(filtered.correct_position(2) == 5)

def test_position_combined():
    input_str = "aabbbbcc"
    filtered = PositionInputFilter(input_str, 2)
    filtered = PositionInputFilter(filtered, 2)
    s = filtered.get_string()
    assert(s == "bbcc")
    assert(filtered.correct_position(2) == 6)

def test_regex_simple():
    input_str = "bbcc"
    # simple replacement, shorter
    filtered = PatternInputFilter(input_str, re.compile("bc"), "d")
    s = filtered.get_string()
    assert(s == "bdc")
    assert(filtered.correct_position(3) == 4) # bdc| -> bbcc|
    assert(filtered.correct_position(2) == 3) # bd|c -> bbc|c
    assert(filtered.correct_position(1) == 1) # b|dc -> b|bcc
    # simple replacement, longer
    filtered = PatternInputFilter(input_str, re.compile("bc"), "dddd")
    s = filtered.get_string()
    assert(s == "bddddc")
    assert(filtered.correct_position(6) == 4) # bddddc| -> bbcc|
    assert(filtered.correct_position(5) == 3) # bdddd|c -> bbc|c
    assert(filtered.correct_position(4) == 2) # bddd|dc -> bb|cc
    assert(filtered.correct_position(3) == 2) # bdd|ddc -> bb|cc
    assert(filtered.correct_position(2) == 2) # bd|dddc -> bb|cc
    assert(filtered.correct_position(1) == 1) # b|ddddc -> b|bcc
    assert(filtered.correct_position(0) == 0) # |bddddc -> |bbcc
    # complex replacement
    filtered = PatternInputFilter(input_str, re.compile(r"(b)bc(c)"), r"\2d\1")
    s = filtered.get_string()
    assert(s == "cdb")
    assert(filtered.correct_position(3) == 4) # cdb| -> bbcc|
    assert(filtered.correct_position(2) == 2) # cd|b -> bb|cc
    assert(filtered.correct_position(1) == 1) # c|db -> b|bcc
    assert(filtered.correct_position(0) == 0) # |cdb -> |bbcc

def test_regex_chained():
    input_str = "bbbcc"
    filtered = PatternInputFilter(input_str, re.compile("[ab]c"), "d") # -> bbdc
    filtered = PatternInputFilter(filtered, re.compile("bd"), "efgh") # -> befc
    s = filtered.get_string()
    assert(filtered.correct_position(6) == 5) # befghc| -> bbbcc|
    assert(filtered.correct_position(5) == 4) # befgh|c -> bbbc|c
    assert(filtered.correct_position(4) == 2) # befg|hc -> bb|bcc
    assert(filtered.correct_position(3) == 2) # bef|ghc -> bb|bcc
    assert(filtered.correct_position(2) == 2) # be|fghc -> bb|bcc
    assert(filtered.correct_position(1) == 1) # b|efghc -> b|bbcc
    assert(filtered.correct_position(0) == 0) # |befghc -> |bbbcc

def test():
    test_position_simple()
    test_position_combined()
    test_regex_simple()
    test_bisect()
    test_regex_chained()

test()