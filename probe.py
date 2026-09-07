#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probe.py — Free signal discovery tool for local GGUF coding models.

Runs a standard 42-task coding bank against your local model, captures
per-token entropy trajectories, scans ~15 candidate wrongness signals
with permutation tests and Benjamini-Hochberg correction, and prints an
honest verdict: does this model have a usable entropy signal that
separates correct from incorrect code generation?

This is the stripped-down free version of the calibration kit. It finds
the signal; the full kit (https://github.com/charlesdvaught-hash/calibration-kit-public)
adds 170-candidate breadth, intervention routing, a live proxy, and
nightly relearning.

Requirements:
    pip install llama-cpp-python numpy

Usage:
    python probe.py --model your-model.gguf
    python probe.py --model your-model.gguf --temp 0.6 --top-p 0.95
    python probe.py --model your-model.gguf --thinking
    python probe.py --model your-model.gguf --repeats 2

What gets sent if you opt in to upload:
    - Model filename and quant label (parsed from filename)
    - Per-task 16-point downsampled entropy trajectory + pass/fail
    - Signal scan results (which signals survived, d values, p values)
    - Timestamp
    - NO prompts, NO generated code, NO user identity, NO IP address

License: CC-BY-4.0 for this file (see LICENSE-CONTENT.md).
The full calibration kit is commercial software under a separate EULA.
"""
import sys
import os
import json
import time
import math
import re
import argparse
import tempfile
import subprocess
import random
from typing import List, Dict, Any, Tuple, Optional

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError, OSError):
        pass

# ─── Constants ────────────────────────────────────────────────────────────────

ALPHA = 0.05
PERM_ITERS = 10000
PERM_SEED = 20260904
MDE_CONST = 2.80  # z(0.975) + z(0.80)
TOPK = 20
PLATEAU_THRESHOLD = 0.5
PLATEAU_MIN_RUN = 3
DS_POINTS = 16
GEN_TIMEOUT_S = 120

_PUNCT_CHARS = frozenset('.,;:!?()[]{}=+-*/<>|&"\'@#`~^%\\')

# Opt-in upload endpoint. Set via environment variable or --upload-url.
# If empty, the upload step is skipped entirely.
DEFAULT_UPLOAD_URL = os.environ.get("PROBE_UPLOAD_URL", "")

# Hard tasks (74 HumanEval-derived tasks with adversarial edge cases).
# Merged with FUNCTION_TASKS into ALL_TASKS, sorted easy→hard.
# The probe stops after collecting enough failures (--target-failures),
# so strong models skip tasks they'd obviously pass and weak models
# stop early once they've failed enough.
_HARD_TASKS_AVAILABLE = False
try:
    from _hard_tasks import HARD_TASKS, HARD_REFERENCES, validate_hard
    _HARD_TASKS_AVAILABLE = True
except ImportError:
    HARD_TASKS = []
    HARD_REFERENCES = {}

# ─── Task bank (42 single-function coding tasks) ──────────────────────────────

FUNCTION_TASKS = [
    {"id": "base_convert", "filename": "base_convert.py", "func_name": "to_base",
     "desc": "Build a Python module with a function to_base(n, b) that converts the integer n to a string in base b, where b is between 2 and 36 inclusive. Digits above 9 use lowercase letters, so 10 is 'a' and 35 is 'z'. to_base(0, 2) returns '0'. Negative numbers get a leading '-', so to_base(-5, 2) returns '-101'. There are no leading zeros otherwise.",
     "tests": [("to_base(0, 2)", "'0'"), ("to_base(-5, 2)", "'-101'"), ("to_base(255, 16)", "'ff'"), ("to_base(35, 36)", "'z'"), ("to_base(1000, 7)", "'2626'")]},
    {"id": "spiral_order", "filename": "spiral_order.py", "func_name": "spiral_order",
     "desc": "Build a Python module with a function spiral_order(matrix) that returns all elements of a rectangular matrix (a list of equal-length lists) in clockwise spiral order, starting at the top-left and moving right first. spiral_order([]) returns []. The matrix may be any width and height, including a single row or a single column.",
     "tests": [("spiral_order([[1,2,3],[4,5,6],[7,8,9]])", "[1,2,3,6,9,8,7,4,5]"), ("spiral_order([])", "[]"), ("spiral_order([[1,2,3,4]])", "[1,2,3,4]"), ("spiral_order([[1],[2],[3]])", "[1,2,3]"), ("spiral_order([[1,2],[3,4],[5,6]])", "[1,2,4,6,5,3]")]},
    {"id": "word_wrap", "filename": "word_wrap.py", "func_name": "wrap",
     "desc": "Build a Python module with a function wrap(text, width) that greedily wraps text to lines of at most `width` characters and returns a list of lines. Split the text on whitespace into words; put as many words on a line as fit, joined by single spaces. A word longer than width goes on a line by itself and is not broken. wrap('', 5) returns []. Lines have no leading or trailing spaces.",
     "tests": [("wrap('the quick brown fox', 10)", "['the quick', 'brown fox']"), ("wrap('', 5)", "[]"), ("wrap('extraordinarily long', 5)", "['extraordinarily', 'long']"), ("wrap('a b c', 1)", "['a', 'b', 'c']"), ("wrap('aa bb cc dd', 5)", "['aa bb', 'cc dd']")]},
    {"id": "roman_to_int", "filename": "roman_to_int.py", "func_name": "roman_to_int",
     "desc": "Build a Python module with a function roman_to_int(s) that converts a valid uppercase Roman numeral string to an integer. The symbols are I=1, V=5, X=10, L=50, C=100, D=500, M=1000. A symbol placed before a larger one is subtracted, so 'IV' is 4 and 'CM' is 900. roman_to_int('') returns 0.",
     "tests": [("roman_to_int('IV')", "4"), ("roman_to_int('')", "0"), ("roman_to_int('MCMXCIV')", "1994"), ("roman_to_int('III')", "3"), ("roman_to_int('LVIII')", "58")]},
    {"id": "int_to_roman", "filename": "int_to_roman.py", "func_name": "int_to_roman",
     "desc": "Build a Python module with a function int_to_roman(n) that converts an integer between 1 and 3999 inclusive to its uppercase Roman numeral string, using the standard subtractive forms IV, IX, XL, XC, CD and CM. int_to_roman(4) returns 'IV'.",
     "tests": [("int_to_roman(4)", "'IV'"), ("int_to_roman(1994)", "'MCMXCIV'"), ("int_to_roman(3999)", "'MMMCMXCIX'"), ("int_to_roman(1)", "'I'"), ("int_to_roman(40)", "'XL'")]},
    {"id": "balanced_brackets", "filename": "balanced_brackets.py", "func_name": "is_balanced",
     "desc": "Build a Python module with a function is_balanced(s) that returns True if every bracket in the string is closed by the matching kind in the correct order, and False otherwise. The bracket kinds are (), [] and {}. Any other character is ignored. is_balanced('') returns True. An unclosed opener returns False.",
     "tests": [("is_balanced('a(b[c]{d})e')", "True"), ("is_balanced('')", "True"), ("is_balanced('([)]')", "False"), ("is_balanced('(')", "False"), ("is_balanced(')(')", "False")]},
    {"id": "longest_common_prefix", "filename": "longest_common_prefix.py", "func_name": "common_prefix",
     "desc": "Build a Python module with a function common_prefix(strs) that returns the longest string that is a prefix of every string in the list strs. Return '' if there is no common prefix, if the list is empty, or if any string is empty. Comparison is case-sensitive.",
     "tests": [("common_prefix(['flower','flow','flight'])", "'fl'"), ("common_prefix([])", "''"), ("common_prefix(['dog','racecar'])", "''"), ("common_prefix(['same','same'])", "'same'"), ("common_prefix(['abc',''])", "''")]},
    {"id": "compress_ranges", "filename": "compress_ranges.py", "func_name": "compress",
     "desc": "Build a Python module with a function compress(nums) that takes a sorted list of unique integers and returns a list of strings describing consecutive runs. A run of one number is reported as 'x'; a run of two or more as 'x->y' using its first and last values. compress([]) returns []. Negative numbers are allowed.",
     "tests": [("compress([0,1,2,4,5,7])", "['0->2','4->5','7']"), ("compress([])", "[]"), ("compress([5])", "['5']"), ("compress([-3,-2,-1,1])", "['-3->-1','1']"), ("compress([1,3,5])", "['1','3','5']")]},
    {"id": "camel_to_snake", "filename": "camel_to_snake.py", "func_name": "to_snake",
     "desc": "Build a Python module with a function to_snake(name) that converts a CamelCase or camelCase identifier to snake_case. Insert an underscore before each uppercase letter that follows a lowercase letter or a digit, and before the last uppercase letter of a run of uppercase letters that is followed by a lowercase letter. Then lowercase everything. to_snake('HTTPServer') returns 'http_server'. to_snake('') returns ''.",
     "tests": [("to_snake('CamelCase')", "'camel_case'"), ("to_snake('HTTPServer')", "'http_server'"), ("to_snake('')", "''"), ("to_snake('parseHTTP2Response')", "'parse_http2_response'"), ("to_snake('already_snake')", "'already_snake'")]},
    {"id": "flatten_dict", "filename": "flatten_dict.py", "func_name": "flatten",
     "desc": "Build a Python module with a function flatten(d) that flattens a nested dictionary into a single-level dictionary whose keys are the paths joined by '.'. Only dict values are recursed into; lists and every other value are left as they are. An empty dict as a value disappears entirely, contributing no key. flatten({}) returns {}.",
     "tests": [("flatten({'a': {'b': 1}, 'c': 2})", "{'a.b': 1, 'c': 2}"), ("flatten({})", "{}"), ("flatten({'a': {'b': {'c': 3}}})", "{'a.b.c': 3}"), ("flatten({'a': {}, 'b': 1})", "{'b': 1}"), ("flatten({'a': [1, {'b': 2}]})", "{'a': [1, {'b': 2}]}")]},
    {"id": "parse_query", "filename": "parse_query.py", "func_name": "parse_query",
     "desc": "Build a Python module with a function parse_query(qs) that parses a URL query string into a dict. Pairs are separated by '&' and key from value by the first '=' only, so 'a=b=c' gives the value 'b=c'. A key with no '=' maps to ''. A repeated key keeps the LAST value. Empty segments are skipped, so 'a=1&&b=2' has two keys. No percent-decoding is performed. parse_query('') returns {}.",
     "tests": [("parse_query('a=1&b=2')", "{'a': '1', 'b': '2'}"), ("parse_query('')", "{}"), ("parse_query('a=b=c')", "{'a': 'b=c'}"), ("parse_query('flag&x=1')", "{'flag': '', 'x': '1'}"), ("parse_query('k=1&&k=2')", "{'k': '2'}")]},
    {"id": "next_permutation", "filename": "next_permutation.py", "func_name": "next_permutation",
     "desc": "Build a Python module with a function next_permutation(nums) that returns a NEW list holding the next lexicographically greater permutation of the list nums. If no greater permutation exists, return the list sorted ascending (the lowest permutation). The input list must not be modified. next_permutation([]) returns [].",
     "tests": [("next_permutation([1,2,3])", "[1,3,2]"), ("next_permutation([3,2,1])", "[1,2,3]"), ("next_permutation([1,1,5])", "[1,5,1]"), ("next_permutation([])", "[]"), ("next_permutation([2,3,1])", "[3,1,2]")]},
    {"id": "group_anagrams", "filename": "group_anagrams.py", "func_name": "group_anagrams",
     "desc": "Build a Python module with a function group_anagrams(words) that groups words that are anagrams of each other. Return a list of groups; each group is a list of words in the order they appeared in the input, and the groups themselves are ordered by where their first member appeared. Comparison is case-sensitive. group_anagrams([]) returns [].",
     "tests": [("group_anagrams(['eat','tea','tan','ate','nat','bat'])", "[['eat','tea','ate'],['tan','nat'],['bat']]"), ("group_anagrams([])", "[]"), ("group_anagrams([''])", "[['']]"), ("group_anagrams(['a'])", "[['a']]"), ("group_anagrams(['ab','ba','AB'])", "[['ab','ba'],['AB']]")]},
    {"id": "search_insert", "filename": "search_insert.py", "func_name": "search_insert",
     "desc": "Build a Python module with a function search_insert(nums, target) that returns the index of target in the sorted list nums, or, if target is absent, the index where it would be inserted to keep the list sorted. If nums contains duplicates of target, return the index of the FIRST occurrence. search_insert([], 1) returns 0.",
     "tests": [("search_insert([1,3,5,6], 5)", "2"), ("search_insert([1,3,5,6], 2)", "1"), ("search_insert([], 1)", "0"), ("search_insert([1,3,5,6], 7)", "4"), ("search_insert([2,2,2], 2)", "0")]},
    {"id": "rle_encode", "filename": "rle_encode.py", "func_name": "rle_encode",
     "desc": "Build a Python module with a function rle_encode(s) that run-length encodes a string. Each run of the same character becomes the character followed by its count, but a run of length 1 is written as the bare character with no count. rle_encode('aaabb') returns 'a3b2'. rle_encode('abc') returns 'abc'. rle_encode('') returns ''.",
     "tests": [("rle_encode('aaabb')", "'a3b2'"), ("rle_encode('abc')", "'abc'"), ("rle_encode('')", "''"), ("rle_encode('aaaaaaaaaa')", "'a10'"), ("rle_encode('aabaa')", "'a2ba2'")]},
    {"id": "valid_ipv4", "filename": "valid_ipv4.py", "func_name": "is_valid_ipv4",
     "desc": "Build a Python module with a function is_valid_ipv4(s) that returns True if s is a valid dotted-quad IPv4 address. There must be exactly four parts separated by '.', each part must be all digits, each must be between 0 and 255 inclusive, and no part may have a leading zero unless the part is exactly '0'. Anything else returns False.",
     "tests": [("is_valid_ipv4('192.168.0.1')", "True"), ("is_valid_ipv4('256.1.1.1')", "False"), ("is_valid_ipv4('01.1.1.1')", "False"), ("is_valid_ipv4('1.1.1')", "False"), ("is_valid_ipv4('0.0.0.0')", "True")]},
    {"id": "rotate_matrix", "filename": "rotate_matrix.py", "func_name": "rotate",
     "desc": "Build a Python module with a function rotate(matrix) that returns a NEW square matrix rotated 90 degrees clockwise. The input is a list of equal-length lists and must not be modified. rotate([]) returns []. A 1x1 matrix is returned unchanged.",
     "tests": [("rotate([[1,2],[3,4]])", "[[3,1],[4,2]]"), ("rotate([])", "[]"), ("rotate([[5]])", "[[5]]"), ("rotate([[1,2,3],[4,5,6],[7,8,9]])", "[[7,4,1],[8,5,2],[9,6,3]]"), ("rotate([[1,2],[3,4],[5,6]])", "[[5,3,1],[6,4,2]]")]},
    {"id": "my_atoi", "filename": "my_atoi.py", "func_name": "my_atoi",
     "desc": "Build a Python module with a function my_atoi(s) that parses a leading integer out of a string. Skip leading whitespace, then read an optional single '+' or '-' sign, then read digits until a non-digit or the end. Return the resulting integer. If there are no digits after the optional sign, return 0. Clamp the result to the 32-bit signed range, so anything above 2147483647 returns 2147483647 and anything below -2147483648 returns -2147483648.",
     "tests": [("my_atoi('   -42abc')", "-42"), ("my_atoi('words 99')", "0"), ("my_atoi('')", "0"), ("my_atoi('91283472332')", "2147483647"), ("my_atoi('+-12')", "0")]},
    {"id": "count_islands", "filename": "count_islands.py", "func_name": "count_islands",
     "desc": "Build a Python module with a function count_islands(grid) that counts connected groups of the integer 1 in a rectangular grid of 0s and 1s. Cells are connected only horizontally and vertically, never diagonally. The grid must not be modified. count_islands([]) returns 0.",
     "tests": [("count_islands([[1,1,0],[0,1,0],[0,0,1]])", "2"), ("count_islands([])", "0"), ("count_islands([[0,0],[0,0]])", "0"), ("count_islands([[1,0,1],[0,0,0],[1,0,1]])", "4"), ("count_islands([[1,1],[1,1]])", "1")]},
    {"id": "longest_unique_substring", "filename": "longest_unique_substring.py", "func_name": "longest_unique",
     "desc": "Build a Python module with a function longest_unique(s) that returns the length of the longest substring of s containing no repeated character. longest_unique('') returns 0. Characters are compared case-sensitively, and whitespace counts as a character.",
     "tests": [("longest_unique('abcabcbb')", "3"), ("longest_unique('')", "0"), ("longest_unique('bbbbb')", "1"), ("longest_unique('pwwkew')", "3"), ("longest_unique('aAbB')", "4")]},
    {"id": "merge_k_sorted", "filename": "merge_k_sorted.py", "func_name": "merge_sorted",
     "desc": "Build a Python module with a function merge_sorted(lists) that merges any number of ascending-sorted integer lists into a single ascending-sorted list containing every element, duplicates included. Empty inner lists are allowed and contribute nothing. merge_sorted([]) returns [].",
     "tests": [("merge_sorted([[1,4,5],[1,3,4],[2,6]])", "[1,1,2,3,4,4,5,6]"), ("merge_sorted([])", "[]"), ("merge_sorted([[],[]])", "[]"), ("merge_sorted([[1]])", "[1]"), ("merge_sorted([[2,2],[2]])", "[2,2,2]")]},
    {"id": "eval_rpn", "filename": "eval_rpn.py", "func_name": "eval_rpn",
     "desc": "Build a Python module with a function eval_rpn(tokens) that evaluates a list of reverse-Polish-notation tokens and returns an integer. Operators are '+', '-', '*' and '/'; every other token is an integer literal, possibly negative. Division truncates toward zero, so 7/-2 is -3. The expression is always valid. eval_rpn([]) returns 0.",
     "tests": [("eval_rpn(['2','1','+','3','*'])", "9"), ("eval_rpn([])", "0"), ("eval_rpn(['4','13','5','/','+'])", "6"), ("eval_rpn(['7','-2','/'])", "-3"), ("eval_rpn(['-5'])", "-5")]},
    {"id": "edit_distance", "filename": "edit_distance.py", "func_name": "edit_distance",
     "desc": "Build a Python module with a function edit_distance(a, b) that returns the Levenshtein distance between two strings: the least number of single-character insertions, deletions or substitutions needed to turn a into b. edit_distance('', '') returns 0 and edit_distance('abc', '') returns 3.",
     "tests": [("edit_distance('kitten','sitting')", "3"), ("edit_distance('','')", "0"), ("edit_distance('abc','')", "3"), ("edit_distance('same','same')", "0"), ("edit_distance('a','b')", "1")]},
    {"id": "chunk_list", "filename": "chunk_list.py", "func_name": "chunk",
     "desc": "Build a Python module with a function chunk(items, size) that splits a list into consecutive chunks of length `size`, returned as a list of lists. The final chunk may be shorter if the list does not divide evenly. chunk([], 3) returns []. If size is less than 1, return [].",
     "tests": [("chunk([1,2,3,4,5], 2)", "[[1,2],[3,4],[5]]"), ("chunk([], 3)", "[]"), ("chunk([1,2,3], 5)", "[[1,2,3]]"), ("chunk([1,2,3], 0)", "[]"), ("chunk([1,2,3,4], 4)", "[[1,2,3,4]]")]},
    {"id": "sort_by_frequency", "filename": "sort_by_frequency.py", "func_name": "by_frequency",
     "desc": "Build a Python module with a function by_frequency(items) that returns the distinct items ordered by how often they appear, most frequent first. Items with the same count keep the order in which they first appeared in the input. by_frequency([]) returns [].",
     "tests": [("by_frequency(['a','b','a','c','b','a'])", "['a','b','c']"), ("by_frequency([])", "[]"), ("by_frequency([1,2,3])", "[1,2,3]"), ("by_frequency([3,3,1,1,2])", "[3,1,2]"), ("by_frequency(['x'])", "['x']")]},
    {"id": "product_except_self", "filename": "product_except_self.py", "func_name": "product_except_self",
     "desc": "Build a Python module with a function product_except_self(nums) that returns a list where each position holds the product of every other element of nums. Do not use division. product_except_self([]) returns []. A single-element list returns [1]. Zeros in the input are handled by the same rule as any other value.",
     "tests": [("product_except_self([1,2,3,4])", "[24,12,8,6]"), ("product_except_self([])", "[]"), ("product_except_self([5])", "[1]"), ("product_except_self([0,4,0])", "[0,0,0]"), ("product_except_self([1,0,3])", "[0,3,0]")]},
    {"id": "interval_intersection", "filename": "interval_intersection.py", "func_name": "intersect",
     "desc": "Build a Python module with a function intersect(a, b) that takes two lists of [start, end] intervals, each list already sorted by start and internally non-overlapping, and returns the list of intervals covered by both. Intervals are inclusive, so [1,3] and [3,5] intersect at [3,3]. Return [] if either list is empty.",
     "tests": [("intersect([[0,2],[5,10]], [[1,5],[8,12]])", "[[1,2],[5,5],[8,10]]"), ("intersect([], [[1,2]])", "[]"), ("intersect([[1,3]], [[3,5]])", "[[3,3]]"), ("intersect([[1,2]], [[3,4]])", "[]"), ("intersect([[1,10]], [[2,3],[5,6]])", "[[2,3],[5,6]]")]},
    {"id": "justify_text", "filename": "justify_text.py", "func_name": "justify",
     "desc": "Build a Python module with a function justify(words, width) that fully justifies text. Greedily pack as many words as fit on each line (words separated by at least one space). Pad each line to exactly `width` characters by distributing spaces as evenly as possible between words, giving the extra spaces to the LEFTMOST gaps first. The last line, and any line holding a single word, is left-justified with single spaces and padded on the right. Return a list of lines. justify([], 5) returns [].",
     "tests": [("justify(['This','is','an','example','of','text','justification.'], 16)", "['This    is    an','example  of text','justification.  ']"), ("justify([], 5)", "[]"), ("justify(['a'], 4)", "['a   ']"), ("justify(['what','must','be'], 6)", "['what  ','must  ','be    ']"), ("justify(['ab','cd','ef'], 5)", "['ab cd','ef   ']")]},
    {"id": "caesar_cipher", "filename": "caesar_cipher.py", "func_name": "caesar",
     "desc": "Build a Python module with a function caesar(text, shift) that shifts every ASCII letter forward by `shift` positions, wrapping within its own case. Non-letters are left unchanged. shift may be negative or larger than 26. caesar('abc', 1) returns 'bcd'. caesar('', 5) returns ''.",
     "tests": [("caesar('abc', 1)", "'bcd'"), ("caesar('', 5)", "''"), ("caesar('Zebra!', 1)", "'Afcsb!'"), ("caesar('abc', -1)", "'zab'"), ("caesar('abc', 27)", "'bcd'")]},
    {"id": "palindrome_alnum", "filename": "palindrome_alnum.py", "func_name": "is_palindrome",
     "desc": "Build a Python module with a function is_palindrome(s) that returns True if s reads the same forwards and backwards once every non-alphanumeric character is removed and case is ignored. The empty string is a palindrome. Digits count as alphanumeric.",
     "tests": [("is_palindrome('A man, a plan, a canal: Panama')", "True"), ("is_palindrome('')", "True"), ("is_palindrome('race a car')", "False"), ("is_palindrome('0P')", "False"), ("is_palindrome('12321')", "True")]},
    {"id": "pascal_row", "filename": "pascal_row.py", "func_name": "pascal_row",
     "desc": "Build a Python module with a function pascal_row(n) that returns row n of Pascal's triangle as a list of integers, where row 0 is [1]. pascal_row(4) returns [1,4,6,4,1]. If n is negative, return [].",
     "tests": [("pascal_row(0)", "[1]"), ("pascal_row(4)", "[1,4,6,4,1]"), ("pascal_row(-1)", "[]"), ("pascal_row(1)", "[1,1]"), ("pascal_row(6)", "[1,6,15,20,15,6,1]")]},
    {"id": "digital_root", "filename": "digital_root.py", "func_name": "digital_root",
     "desc": "Build a Python module with a function digital_root(n) that repeatedly sums the decimal digits of the non-negative integer n until a single digit remains, and returns it. digital_root(0) returns 0. digital_root(9875) returns 2.",
     "tests": [("digital_root(0)", "0"), ("digital_root(9875)", "2"), ("digital_root(9)", "9"), ("digital_root(10)", "1"), ("digital_root(199)", "1")]},
    {"id": "min_jumps", "filename": "min_jumps.py", "func_name": "min_jumps",
     "desc": "Build a Python module with a function min_jumps(nums) that returns the least number of jumps needed to reach the last index of the list, starting at index 0, where nums[i] is the maximum jump length from position i. If the last index cannot be reached, return -1. A list of length 0 or 1 needs 0 jumps.",
     "tests": [("min_jumps([2,3,1,1,4])", "2"), ("min_jumps([])", "0"), ("min_jumps([0])", "0"), ("min_jumps([3,2,1,0,4])", "-1"), ("min_jumps([1,1,1,1])", "3")]},
    {"id": "topo_sort", "filename": "topo_sort.py", "func_name": "topo_sort",
     "desc": "Build a Python module with a function topo_sort(nodes, edges) that returns a topological ordering of `nodes` (a list) given `edges` (a list of [a, b] pairs meaning a must come before b). When several nodes are ready at once, take the one that appears earliest in `nodes`. If the graph has a cycle, return []. topo_sort([], []) returns [].",
     "tests": [("topo_sort(['a','b','c'], [['a','b'],['b','c']])", "['a','b','c']"), ("topo_sort([], [])", "[]"), ("topo_sort(['a','b'], [['a','b'],['b','a']])", "[]"), ("topo_sort(['c','a','b'], [['a','b']])", "['c','a','b']"), ("topo_sort(['a','b','c'], [])", "['a','b','c']")]},
    {"id": "dedupe_ordered", "filename": "dedupe_ordered.py", "func_name": "dedupe",
     "desc": "Build a Python module with a function dedupe(items) that returns a new list with duplicates removed, keeping the FIRST occurrence of each value and the original order. The input must not be modified. dedupe([]) returns []. Values that compare equal are treated as duplicates.",
     "tests": [("dedupe([1,2,1,3,2])", "[1,2,3]"), ("dedupe([])", "[]"), ("dedupe(['a','a','a'])", "['a']"), ("dedupe([3,2,1])", "[3,2,1]"), ("dedupe([0,False,1])", "[0,1]")]},
    {"id": "moving_average", "filename": "moving_average.py", "func_name": "moving_average",
     "desc": "Build a Python module with a function moving_average(nums, k) that returns the list of averages of every consecutive window of length k, each rounded to 2 decimal places with the built-in round. If k is less than 1 or greater than the length of nums, return []. moving_average([], 1) returns [].",
     "tests": [("moving_average([1,2,3,4], 2)", "[1.5, 2.5, 3.5]"), ("moving_average([], 1)", "[]"), ("moving_average([1,2], 3)", "[]"), ("moving_average([1,2,3], 3)", "[2.0]"), ("moving_average([1,1,4], 2)", "[1.0, 2.5]")]},
    {"id": "gcd_lcm", "filename": "gcd_lcm.py", "func_name": "gcd_lcm",
     "desc": "Build a Python module with a function gcd_lcm(a, b) that returns the tuple (gcd, lcm) of two non-negative integers. The gcd of 0 and 0 is 0, and their lcm is also 0. When either value is 0 the lcm is 0. gcd_lcm(12, 18) returns (6, 36).",
     "tests": [("gcd_lcm(12, 18)", "(6, 36)"), ("gcd_lcm(0, 0)", "(0, 0)"), ("gcd_lcm(0, 5)", "(5, 0)"), ("gcd_lcm(7, 13)", "(1, 91)"), ("gcd_lcm(4, 4)", "(4, 4)")]},
    {"id": "two_sum_sorted", "filename": "two_sum_sorted.py", "func_name": "two_sum",
     "desc": "Build a Python module with a function two_sum(nums, target) that finds two DIFFERENT positions in the ascending-sorted list nums whose values add up to target, and returns them as a list of two zero-based indices in increasing order. If several pairs work, return the one with the smallest first index; if that ties, the smallest second index. Return [] if no pair works.",
     "tests": [("two_sum([2,7,11,15], 9)", "[0,1]"), ("two_sum([2,3,4], 6)", "[0,2]"), ("two_sum([], 1)", "[]"), ("two_sum([1,2], 100)", "[]"), ("two_sum([0,0,3], 0)", "[0,1]")]},
    {"id": "expand_tabs", "filename": "expand_tabs.py", "func_name": "expand_tabs",
     "desc": "Build a Python module with a function expand_tabs(line, tabsize) that replaces every tab character with spaces up to the next tab stop. Tab stops sit at every multiple of tabsize counted from the start of the line, so a tab always inserts at least one space. Other characters are copied unchanged and each advances the column by one. expand_tabs('', 4) returns ''. If tabsize is less than 1, return the line unchanged.",
     "tests": [("expand_tabs('a\\tb', 4)", "'a   b'"), ("expand_tabs('', 4)", "''"), ("expand_tabs('\\t', 4)", "'    '"), ("expand_tabs('abcd\\te', 4)", "'abcd    e'"), ("expand_tabs('a\\tb', 0)", "'a\\tb'")]},
    {"id": "version_compare", "filename": "version_compare.py", "func_name": "compare_versions",
     "desc": "Build a Python module with a function compare_versions(a, b) that compares two dot-separated version strings numerically and returns -1 if a is older, 1 if a is newer, and 0 if they are equal. Each part is an integer, leading zeros are allowed and insignificant, and a missing trailing part counts as 0, so '1.0' equals '1'.",
     "tests": [("compare_versions('1.0', '1')", "0"), ("compare_versions('1.2', '1.10')", "-1"), ("compare_versions('2.0', '1.9.9')", "1"), ("compare_versions('1.01', '1.1')", "0"), ("compare_versions('1.0.0', '1.0.1')", "-1")]},
    {"id": "csv_split", "filename": "csv_split.py", "func_name": "split_csv_line",
     "desc": "Build a Python module with a function split_csv_line(line) that splits one line of CSV into a list of field strings. A field wrapped in double quotes may contain commas and doubled quotes: inside a quoted field, '\"\"' means one literal quote character. Quotes are removed from the result. Unquoted fields are taken as-is with no trimming. split_csv_line('') returns [''].",
     "tests": [("split_csv_line('a,b,c')", "['a','b','c']"), ("split_csv_line('')", "['']"), ("split_csv_line('a,\"b,c\",d')", "['a','b,c','d']"), ("split_csv_line('\"say \"\"hi\"\"\",x')", "['say \"hi\"','x']"), ("split_csv_line('a,,b')", "['a','','b']")]},
    {"id": "binary_gap", "filename": "binary_gap.py", "func_name": "binary_gap",
     "desc": "Build a Python module with a function binary_gap(n) that returns the length of the longest run of consecutive zeros in the binary representation of the positive integer n that is bounded by a 1 on both sides. If there is no such run, return 0. binary_gap(9) is 2 because 9 is 1001. binary_gap(0) returns 0.",
     "tests": [("binary_gap(9)", "2"), ("binary_gap(0)", "0"), ("binary_gap(529)", "4"), ("binary_gap(20)", "1"), ("binary_gap(15)", "0")]},
]

REFERENCES = {
    'balanced_brackets': '\ndef is_balanced(s):\n    pairs = {")": "(", "]": "[", "}": "{"}\n    stack = []\n    for ch in s:\n        if ch in "([{":\n            stack.append(ch)\n        elif ch in pairs:\n            if not stack or stack.pop() != pairs[ch]:\n                return False\n    return not stack\n',
    'base_convert': '\ndef to_base(n, b):\n    if n == 0:\n        return "0"\n    digits = "0123456789abcdefghijklmnopqrstuvwxyz"\n    neg = n < 0\n    n = abs(n)\n    out = []\n    while n:\n        out.append(digits[n % b])\n        n //= b\n    if neg:\n        out.append("-")\n    return "".join(reversed(out))\n',
    'binary_gap': '\ndef binary_gap(n):\n    if n <= 0:\n        return 0\n    bits = bin(n)[2:]\n    best = 0\n    cur = None\n    for ch in bits:\n        if ch == "1":\n            if cur is not None:\n                best = max(best, cur)\n            cur = 0\n        elif cur is not None:\n            cur += 1\n    return best\n',
    'caesar_cipher': '\ndef caesar(text, shift):\n    out = []\n    for ch in text:\n        if "a" <= ch <= "z":\n            out.append(chr((ord(ch) - 97 + shift) % 26 + 97))\n        elif "A" <= ch <= "Z":\n            out.append(chr((ord(ch) - 65 + shift) % 26 + 65))\n        else:\n            out.append(ch)\n    return "".join(out)\n',
    'camel_to_snake': '\nimport re\n\n\ndef to_snake(name):\n    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\\1_\\2", name)\n    s = re.sub(r"([a-z0-9])([A-Z])", r"\\1_\\2", s)\n    return s.lower()\n',
    'chunk_list': '\ndef chunk(items, size):\n    if size < 1:\n        return []\n    return [list(items[i:i + size]) for i in range(0, len(items), size)]\n',
    'compress_ranges': '\ndef compress(nums):\n    if not nums:\n        return []\n    out = []\n    start = prev = nums[0]\n    for n in nums[1:]:\n        if n == prev + 1:\n            prev = n\n            continue\n        out.append(str(start) if start == prev else str(start) + "->" + str(prev))\n        start = prev = n\n    out.append(str(start) if start == prev else str(start) + "->" + str(prev))\n    return out\n',
    'count_islands': '\ndef count_islands(grid):\n    if not grid or not grid[0]:\n        return 0\n    rows, cols = len(grid), len(grid[0])\n    seen = set()\n    count = 0\n    for r in range(rows):\n        for c in range(cols):\n            if grid[r][c] != 1 or (r, c) in seen:\n                continue\n            count += 1\n            stack = [(r, c)]\n            seen.add((r, c))\n            while stack:\n                y, x = stack.pop()\n                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):\n                    ny, nx = y + dy, x + dx\n                    if 0 <= ny < rows and 0 <= nx < cols:\n                        if grid[ny][nx] == 1 and (ny, nx) not in seen:\n                            seen.add((ny, nx))\n                            stack.append((ny, nx))\n    return count\n',
    'csv_split': '\ndef split_csv_line(line):\n    fields = []\n    cur = []\n    i = 0\n    in_quotes = False\n    while i < len(line):\n        ch = line[i]\n        if in_quotes:\n            if ch == \'"\':\n                if i + 1 < len(line) and line[i + 1] == \'"\':\n                    cur.append(\'"\')\n                    i += 2\n                    continue\n                in_quotes = False\n            else:\n                cur.append(ch)\n        else:\n            if ch == \'"\':\n                in_quotes = True\n            elif ch == ",":\n                fields.append("".join(cur))\n                cur = []\n            else:\n                cur.append(ch)\n        i += 1\n    fields.append("".join(cur))\n    return fields\n',
    'dedupe_ordered': '\ndef dedupe(items):\n    seen = set()\n    out = []\n    for it in items:\n        if it not in seen:\n            seen.add(it)\n            out.append(it)\n    return out\n',
    'digital_root': '\ndef digital_root(n):\n    while n > 9:\n        n = sum(int(c) for c in str(n))\n    return n\n',
    'edit_distance': '\ndef edit_distance(a, b):\n    prev = list(range(len(b) + 1))\n    for i, ca in enumerate(a, 1):\n        cur = [i]\n        for j, cb in enumerate(b, 1):\n            cur.append(min(prev[j] + 1, cur[j - 1] + 1,\n                           prev[j - 1] + (ca != cb)))\n        prev = cur\n    return prev[-1]\n',
    'eval_rpn': '\ndef eval_rpn(tokens):\n    if not tokens:\n        return 0\n    stack = []\n    for t in tokens:\n        if t in ("+", "-", "*", "/"):\n            b = stack.pop()\n            a = stack.pop()\n            if t == "+":\n                stack.append(a + b)\n            elif t == "-":\n                stack.append(a - b)\n            elif t == "*":\n                stack.append(a * b)\n            else:\n                stack.append(int(a / b))\n        else:\n            stack.append(int(t))\n    return stack[-1]\n',
    'expand_tabs': '\ndef expand_tabs(line, tabsize):\n    if tabsize < 1:\n        return line\n    out = []\n    col = 0\n    for ch in line:\n        if ch == "\\t":\n            pad = tabsize - (col % tabsize)\n            out.append(" " * pad)\n            col += pad\n        else:\n            out.append(ch)\n            col += 1\n    return "".join(out)\n',
    'flatten_dict': '\ndef flatten(d, prefix=""):\n    out = {}\n    for k, v in d.items():\n        key = prefix + str(k)\n        if isinstance(v, dict):\n            out.update(flatten(v, key + "."))\n        else:\n            out[key] = v\n    return out\n',
    'gcd_lcm': '\ndef gcd_lcm(a, b):\n    x, y = a, b\n    while y:\n        x, y = y, x % y\n    g = x\n    lcm = 0 if (a == 0 or b == 0) else a * b // g\n    return (g, lcm)\n',
    'group_anagrams': '\ndef group_anagrams(words):\n    groups = {}\n    order = []\n    for w in words:\n        key = "".join(sorted(w))\n        if key not in groups:\n            groups[key] = []\n            order.append(key)\n        groups[key].append(w)\n    return [groups[k] for k in order]\n',
    'int_to_roman': '\ndef int_to_roman(n):\n    table = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),\n             (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),\n             (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]\n    out = []\n    for v, sym in table:\n        while n >= v:\n            out.append(sym)\n            n -= v\n    return "".join(out)\n',
    'interval_intersection': '\ndef intersect(a, b):\n    out = []\n    i = j = 0\n    while i < len(a) and j < len(b):\n        lo = max(a[i][0], b[j][0])\n        hi = min(a[i][1], b[j][1])\n        if lo <= hi:\n            out.append([lo, hi])\n        if a[i][1] < b[j][1]:\n            i += 1\n        else:\n            j += 1\n    return out\n',
    'justify_text': '\ndef justify(words, width):\n    if not words:\n        return []\n    lines = []\n    cur = []\n    cur_len = 0\n    for w in words:\n        if cur and cur_len + len(cur) + len(w) > width:\n            lines.append(cur)\n            cur, cur_len = [], 0\n        cur.append(w)\n        cur_len += len(w)\n    lines.append(cur)\n    out = []\n    for idx, line in enumerate(lines):\n        if idx == len(lines) - 1 or len(line) == 1:\n            s = " ".join(line)\n            out.append(s + " " * (width - len(s)))\n        else:\n            total_spaces = width - sum(len(w) for w in line)\n            gaps = len(line) - 1\n            base, extra = divmod(total_spaces, gaps)\n            s = ""\n            for i, w in enumerate(line[:-1]):\n                s += w + " " * (base + (1 if i < extra else 0))\n            s += line[-1]\n            out.append(s)\n    return out\n',
    'longest_common_prefix': '\ndef common_prefix(strs):\n    if not strs:\n        return ""\n    out = []\n    for chars in zip(*strs):\n        if len(set(chars)) == 1:\n            out.append(chars[0])\n        else:\n            break\n    return "".join(out)\n',
    'longest_unique_substring': '\ndef longest_unique(s):\n    last = {}\n    best = start = 0\n    for i, ch in enumerate(s):\n        if ch in last and last[ch] >= start:\n            start = last[ch] + 1\n        last[ch] = i\n        best = max(best, i - start + 1)\n    return best\n',
    'merge_k_sorted': '\ndef merge_sorted(lists):\n    out = []\n    for lst in lists:\n        out.extend(lst)\n    return sorted(out)\n',
    'min_jumps': '\ndef min_jumps(nums):\n    n = len(nums)\n    if n <= 1:\n        return 0\n    jumps = 0\n    cur_end = 0\n    farthest = 0\n    for i in range(n - 1):\n        if i > farthest:\n            return -1\n        farthest = max(farthest, i + nums[i])\n        if i == cur_end:\n            jumps += 1\n            cur_end = farthest\n            if cur_end >= n - 1:\n                return jumps\n    return -1 if farthest < n - 1 else jumps\n',
    'moving_average': '\ndef moving_average(nums, k):\n    if k < 1 or k > len(nums):\n        return []\n    out = []\n    for i in range(len(nums) - k + 1):\n        out.append(round(sum(nums[i:i + k]) / k, 2))\n    return out\n',
    'my_atoi': '\ndef my_atoi(s):\n    i, n = 0, len(s)\n    while i < n and s[i].isspace():\n        i += 1\n    sign = 1\n    if i < n and s[i] in "+-":\n        sign = -1 if s[i] == "-" else 1\n        i += 1\n    start = i\n    while i < n and s[i].isdigit():\n        i += 1\n    if i == start:\n        return 0\n    val = sign * int(s[start:i])\n    return max(-2147483648, min(2147483647, val))\n',
    'next_permutation': '\ndef next_permutation(nums):\n    a = list(nums)\n    i = len(a) - 2\n    while i >= 0 and a[i] >= a[i + 1]:\n        i -= 1\n    if i < 0:\n        return sorted(a)\n    j = len(a) - 1\n    while a[j] <= a[i]:\n        j -= 1\n    a[i], a[j] = a[j], a[i]\n    a[i + 1:] = reversed(a[i + 1:])\n    return a\n',
    'palindrome_alnum': '\ndef is_palindrome(s):\n    cleaned = [ch.lower() for ch in s if ch.isalnum()]\n    return cleaned == cleaned[::-1]\n',
    'parse_query': '\ndef parse_query(qs):\n    out = {}\n    for part in qs.split("&"):\n        if not part:\n            continue\n        k, sep, v = part.partition("=")\n        out[k] = v if sep else ""\n    return out\n',
    'pascal_row': '\ndef pascal_row(n):\n    if n < 0:\n        return []\n    row = [1]\n    for k in range(n):\n        row.append(row[-1] * (n - k) // (k + 1))\n    return row\n',
    'product_except_self': '\ndef product_except_self(nums):\n    n = len(nums)\n    if n == 0:\n        return []\n    out = [1] * n\n    left = 1\n    for i in range(n):\n        out[i] = left\n        left *= nums[i]\n    right = 1\n    for i in range(n - 1, -1, -1):\n        out[i] *= right\n        right *= nums[i]\n    return out\n',
    'rle_encode': '\ndef rle_encode(s):\n    if not s:\n        return ""\n    out = []\n    prev, count = s[0], 1\n    for ch in s[1:]:\n        if ch == prev:\n            count += 1\n        else:\n            out.append(prev if count == 1 else prev + str(count))\n            prev, count = ch, 1\n    out.append(prev if count == 1 else prev + str(count))\n    return "".join(out)\n',
    'roman_to_int': '\ndef roman_to_int(s):\n    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}\n    total = 0\n    for i, ch in enumerate(s):\n        v = vals[ch]\n        if i + 1 < len(s) and vals[s[i + 1]] > v:\n            total -= v\n        else:\n            total += v\n    return total\n',
    'rotate_matrix': '\ndef rotate(matrix):\n    if not matrix or not matrix[0]:\n        return []\n    return [list(row) for row in zip(*matrix[::-1])]\n',
    'search_insert': '\ndef search_insert(nums, target):\n    lo, hi = 0, len(nums)\n    while lo < hi:\n        mid = (lo + hi) // 2\n        if nums[mid] < target:\n            lo = mid + 1\n        else:\n            hi = mid\n    return lo\n',
    'sort_by_frequency': '\ndef by_frequency(items):\n    counts = {}\n    order = []\n    for it in items:\n        if it not in counts:\n            counts[it] = 0\n            order.append(it)\n        counts[it] += 1\n    return sorted(order, key=lambda x: -counts[x])\n',
    'spiral_order': '\ndef spiral_order(matrix):\n    if not matrix or not matrix[0]:\n        return []\n    out = []\n    top, bottom = 0, len(matrix) - 1\n    left, right = 0, len(matrix[0]) - 1\n    while top <= bottom and left <= right:\n        for c in range(left, right + 1):\n            out.append(matrix[top][c])\n        top += 1\n        for r in range(top, bottom + 1):\n            out.append(matrix[r][right])\n        right -= 1\n        if top <= bottom:\n            for c in range(right, left - 1, -1):\n                out.append(matrix[bottom][c])\n            bottom -= 1\n        if left <= right:\n            for r in range(bottom, top - 1, -1):\n                out.append(matrix[r][left])\n            left += 1\n    return out\n',
    'topo_sort': '\ndef topo_sort(nodes, edges):\n    indeg = {n: 0 for n in nodes}\n    adj = {n: [] for n in nodes}\n    for a, b in edges:\n        adj[a].append(b)\n        indeg[b] += 1\n    out = []\n    remaining = list(nodes)\n    while remaining:\n        pick = None\n        for n in remaining:\n            if indeg[n] == 0:\n                pick = n\n                break\n        if pick is None:\n            return []\n        remaining.remove(pick)\n        out.append(pick)\n        for nb in adj[pick]:\n            indeg[nb] -= 1\n    return out\n',
    'two_sum_sorted': '\ndef two_sum(nums, target):\n    for i in range(len(nums)):\n        for j in range(i + 1, len(nums)):\n            if nums[i] + nums[j] == target:\n                return [i, j]\n    return []\n',
    'valid_ipv4': '\ndef is_valid_ipv4(s):\n    parts = s.split(".")\n    if len(parts) != 4:\n        return False\n    for p in parts:\n        if not p or not p.isdigit():\n            return False\n        if len(p) > 1 and p[0] == "0":\n            return False\n        if int(p) > 255:\n            return False\n    return True\n',
    'version_compare': '\ndef compare_versions(a, b):\n    pa = [int(x) for x in a.split(".")]\n    pb = [int(x) for x in b.split(".")]\n    for i in range(max(len(pa), len(pb))):\n        va = pa[i] if i < len(pa) else 0\n        vb = pb[i] if i < len(pb) else 0\n        if va < vb:\n            return -1\n        if va > vb:\n            return 1\n    return 0\n',
    'word_wrap': '\ndef wrap(text, width):\n    words = text.split()\n    if not words:\n        return []\n    lines = []\n    cur = words[0]\n    for w in words[1:]:\n        if len(cur) + 1 + len(w) <= width:\n            cur += " " + w\n        else:\n            lines.append(cur)\n            cur = w\n    lines.append(cur)\n    return lines\n',
}

def validate(tasks=None, verbose=True):
    """Validate the task bank by running each reference implementation against
    its own tests. Returns True if all tasks pass."""
    if tasks is None:
        tasks = FUNCTION_TASKS
    import tempfile
    all_ok = True
    for task in tasks:
        ref = REFERENCES.get(task["id"])
        if ref is None:
            if verbose:
                print(f"  {task['id']:<28} SKIP (no reference)")
            continue
        with tempfile.TemporaryDirectory() as td:
            passed, total, failures = test_function_code(ref, task, td)
        ok = (passed == total)
        if not ok:
            all_ok = False
        if verbose:
            status = "OK" if ok else f"FAIL ({passed}/{total})"
            print(f"  {task['id']:<28} {status}")
            if failures:
                for f in failures[:2]:
                    print(f"    {f}")
    return all_ok


# ─── Unified task bank (easy→hard, with early stop) ───────────────────────────

# Merge the 42 easy tasks with the 74 hard tasks into one list,
# sorted by difficulty (code length + test count + spec complexity).
# The probe stops after collecting --target-failures failures, so strong
# models skip tasks they'd obviously pass and weak models stop early.
# The holdout tasks (next N after early stop) land near the model's cusp.
def _difficulty_score(task):
    ref_len = len(task.get("reference", ""))
    n_tests = len(task.get("tests", []))
    desc_len = len(task.get("desc", ""))
    return ref_len * 0.5 + n_tests * 50 + desc_len * 0.1

# All benchmark tasks (150 total), difficulty-sorted by the build script.
# Includes the original 42 easy tasks plus 108 harder HumanEval-derived tasks.
ALL_TASKS = list(HARD_TASKS)

# Minimum failures needed for statistical power.
# Below this, the probe reports UNDERPOWERED regardless of signal strength.
DEFAULT_TARGET_FAILURES = 15

# Minimum failures needed for statistical power.
# Below this, the probe reports UNDERPOWERED regardless of signal strength.
DEFAULT_TARGET_FAILURES = 15


class GenTimeout(Exception):
    pass


class EntropyTrajectory:
    """Collect per-token entropy and shape features from llama-cpp-python logits.

    This is the same math as the full kit's CalibratedEntropyTrajectory, stripped
    to the core: top-20 cropped softmax entropy, structural/semantic split,
    plateau detection, spike location, per-quartile averages, thinking boundary,
    and the one-pass series (full_ent, mass1/5/20, kl_step, kl_cent, margin,
    surprisal, rank). Every numeric field in stats() becomes a candidate signal.
    """

    def __init__(self, blacklist: frozenset, timeout: float = None,
                 think_marker_ids: set = None):
        self.bl = blacklist
        self.deadline = (time.time() + timeout) if timeout else None
        self.structural: List[float] = []
        self.semantic: List[float] = []
        self.semantic_pos: List[int] = []
        self.top1: List[float] = []
        self.margin: List[float] = []
        self.full_ent: List[float] = []
        self.mass1: List[float] = []
        self.mass5: List[float] = []
        self.mass20: List[float] = []
        self.kl_step: List[float] = []
        self.kl_cent: List[float] = []
        self.surprisal: List[float] = []
        self.rank: List[float] = []
        self._prev_idx = None
        self._prev_p = None
        self._cent_sum: Dict[int, float] = {}
        self._cent_n = 0
        self._pos = 0
        self._prev_logits = None
        self._prev_lse = 0.0
        self.think_marker_ids = set(think_marker_ids or [])
        self.think_boundary: Optional[int] = None

    def __call__(self, tokens, logits):
        if self.deadline is not None and time.time() > self.deadline:
            raise GenTimeout("generation exceeded wall-clock budget")
        self._pos += 1
        import numpy as np
        logits = np.asarray(logits, dtype=np.float64)
        # Sampled-token bookkeeping for the token chosen at the PREVIOUS step.
        if self._prev_logits is not None and len(tokens) and self._pos >= 2:
            chosen = int(tokens[-1])
            if 0 <= chosen < self._prev_logits.shape[0]:
                lp = float(self._prev_logits[chosen]) - self._prev_lse
                self.surprisal.append(-lp)
                self.rank.append(float(
                    1 + int((self._prev_logits > self._prev_logits[chosen]).sum())))
            else:
                self.surprisal.append(0.0)
                self.rank.append(0.0)
            if (self.think_boundary is None and self.think_marker_ids
                    and chosen in self.think_marker_ids):
                self.think_boundary = self._pos - 1
        self._prev_lse = float(
            np.log(np.sum(np.exp(logits - np.max(logits)))) + np.max(logits))
        self._prev_logits = logits
        k = TOPK
        top_idx = np.argpartition(logits, -k)[-k:]
        top_sorted = top_idx[np.argsort(logits[top_idx])]
        top20 = logits[top_sorted]
        probs = np.exp(top20 - np.max(top20))
        probs = probs / probs.sum()
        ent = float(-np.sum(probs * np.log(probs + 1e-10)))
        token_id = int(np.argmax(logits))
        if token_id in self.bl:
            self.structural.append(ent)
            return logits
        self.semantic.append(ent)
        self.semantic_pos.append(self._pos - 1)
        self.top1.append(float(probs[-1]))
        self.margin.append(float(probs[-1] - probs[-2]))
        mx = float(np.max(logits))
        e = np.exp(logits - mx)
        total = float(e.sum())
        if total > 0:
            p_full = e / total
            self.full_ent.append(float(-np.sum(p_full * np.log(p_full + 1e-10))))
            c = np.cumsum(p_full[top_sorted[::-1]])
            self.mass1.append(float(c[0]))
            self.mass5.append(float(c[4]))
            self.mass20.append(float(c[k - 1]))
        else:
            self.full_ent.append(0.0)
            self.mass1.append(0.0)
            self.mass5.append(0.0)
            self.mass20.append(0.0)
        cur_idx = top_sorted
        cur_p = probs
        eps = 1e-10
        if self._prev_idx is not None:
            prev = dict(zip(self._prev_idx.tolist(), self._prev_p.tolist()))
            kl = 0.0
            for i, p in zip(cur_idx.tolist(), cur_p.tolist()):
                kl += p * np.log(p / max(prev.get(i, eps), eps))
            self.kl_step.append(float(kl))
        else:
            self.kl_step.append(0.0)
        if self._cent_n > 0:
            kl = 0.0
            for i, p in zip(cur_idx.tolist(), cur_p.tolist()):
                q = self._cent_sum.get(i, 0.0) / self._cent_n
                kl += p * np.log(p / max(q, eps))
            self.kl_cent.append(float(kl))
        else:
            self.kl_cent.append(0.0)
        for i, p in zip(cur_idx.tolist(), cur_p.tolist()):
            self._cent_sum[i] = self._cent_sum.get(i, 0.0) + p
        self._cent_n += 1
        self._prev_idx = cur_idx
        self._prev_p = cur_p
        return logits

    def stats(self) -> Dict[str, Any]:
        s = self.semantic
        if not s:
            empty = self._empty_stats()
            return empty
        n = len(s)
        q1 = max(1, n // 4)
        # Plateau detection
        plateau = False
        plateau_start = -1
        run = 0
        for i in range(n):
            window = s[max(0, i - 3):i + 1]
            if sum(window) / len(window) > PLATEAU_THRESHOLD:
                run += 1
                if run >= PLATEAU_MIN_RUN and plateau_start < 0:
                    plateau = True
                    plateau_start = i - run + 1
            else:
                run = 0
        # Spike location
        max_idx = int(max(range(n), key=lambda i: s[i]))
        spike_quartile = min(3, max_idx * 4 // n)
        # Per-quartile averages
        qsize = max(1, n // 4)
        quartile_ents = []
        for q in range(4):
            start = q * qsize
            end = (q + 1) * qsize if q < 3 else n
            chunk = s[start:end]
            quartile_ents.append(sum(chunk) / len(chunk) if chunk else 0.0)
        # Early-trajectory features
        def _mean(xs):
            return sum(xs) / len(xs) if xs else 0.0
        first10 = s[:10]
        rest = s[10:]
        m10 = _mean(first10)
        k = len(first10)
        if k >= 3:
            xbar = (k - 1) / 2.0
            ybar = m10
            num = sum((i - xbar) * (v - ybar) for i, v in enumerate(first10))
            den = sum((i - xbar) ** 2 for i in range(k))
            early_slope = num / den if den else 0.0
            var10 = sum((v - m10) ** 2 for v in first10) / k
            std10 = var10 ** 0.5
        else:
            early_slope = 0.0
            std10 = 0.0
        mx = max(s)
        q_slope = quartile_ents[3] - quartile_ents[0]
        q_curvature = (quartile_ents[0] + quartile_ents[3]) - 2 * (
            (quartile_ents[1] + quartile_ents[2]) / 2)
        q_argmax = int(max(range(4), key=lambda i: quartile_ents[i]))
        # Downsampled trajectory
        DS = DS_POINTS
        if n >= DS:
            step = n / DS
            trajectory_ds = [round(_mean(s[int(i * step):max(int((i + 1) * step),
                                                            int(i * step) + 1)]), 4)
                             for i in range(DS)]
        else:
            trajectory_ds = [round(v, 4) for v in s]
        # Structural entropy
        st = self.structural
        struct_ent_mean = _mean(st)
        struct_ent_std = (sum((v - struct_ent_mean) ** 2 for v in st)
                          / len(st)) ** 0.5 if st else 0.0
        out = {
            "mean_entropy": sum(s) / n, "max_entropy": mx,
            "first_token_entropy": s[0], "first3_mean": _mean(s[:3]),
            "first5_mean": _mean(s[:5]), "first10_mean": m10,
            "first10_max": max(first10) if first10 else 0.0,
            "first10_std": std10, "early_slope": early_slope,
            "early_vs_rest": m10 - _mean(rest) if rest else 0.0,
            "first_to_max_ratio": (s[0] / mx) if mx > 0 else 0.0,
            "q_slope": q_slope, "q_curvature": q_curvature, "q_argmax": q_argmax,
            "trajectory_ds": trajectory_ds,
            "phi_first": self.top1[0] if self.top1 else 0.0,
            "phi_first10_mean": _mean(self.top1[:10]),
            "phi_mean": _mean(self.top1),
            "margin_first": self.margin[0] if self.margin else 0.0,
            "margin_mean": _mean(self.margin),
            "struct_ent_mean": struct_ent_mean, "struct_ent_std": struct_ent_std,
            "head_entropy": sum(s[:q1]) / q1,
            "tail_entropy": sum(s[-q1:]) / q1 if n > q1 else sum(s) / n,
            "n_tokens": n + len(self.structural), "n_semantic": n,
            "plateau": plateau,
            "plateau_start_quartile": min(3, plateau_start * 4 // n) if plateau_start >= 0 else -1,
            "spike_quartile": spike_quartile, "spike_token_idx": max_idx,
            "spike_relative_pos": max_idx / n,
            "quartile_entropies": [round(q, 4) for q in quartile_ents],
        }
        # One-pass series summaries
        import math as _math
        tail_mass = [1.0 - v for v in self.mass20]
        series = {
            "full_ent": self.full_ent, "mass1": self.mass1,
            "mass5": self.mass5, "mass20": self.mass20,
            "tail_mass": tail_mass, "kl_step": self.kl_step,
            "kl_cent": self.kl_cent, "margin": self.margin,
            "kl_uniform": [_math.log(TOPK) - v for v in s],
            "surprisal": self.surprisal, "rank": self.rank,
        }
        for name, xs in series.items():
            out.update(_series_summary(name, xs))
        # Thinking-phase split
        think_boundary = self.think_boundary
        out["think_boundary"] = think_boundary if think_boundary else 0
        out["think_frac"] = (think_boundary / max(self._pos, 1)
                             if think_boundary else 0.0)
        if think_boundary:
            bidx = sum(1 for p in self.semantic_pos if p < think_boundary)
            phase_series = {"ent": s, "phi": self.top1, "margin": self.margin,
                            "kl_step": self.kl_step, "kl_cent": self.kl_cent,
                            "full_ent": self.full_ent}
            for name, xs in phase_series.items():
                think_xs = xs[:bidx]
                ans_xs = xs[bidx:]
                out[f"think_{name}_mean"] = _mean(think_xs)
                out[f"think_{name}_std"] = (
                    (sum((v - out[f"think_{name}_mean"]) ** 2
                         for v in think_xs) / len(think_xs)) ** 0.5
                    if think_xs else 0.0)
                out[f"answer_{name}_mean"] = _mean(ans_xs)
                out[f"answer_{name}_std"] = (
                    (sum((v - out[f"answer_{name}_mean"]) ** 2
                         for v in ans_xs) / len(ans_xs)) ** 0.5
                    if ans_xs else 0.0)
        # Shape features (derived from quartile entropies + downsampled trajectory)
        out.update(_shape_features(out))
        return out

    def _empty_stats(self) -> Dict[str, Any]:
        empty = {
            "mean_entropy": 0, "max_entropy": 0, "head_entropy": 0,
            "tail_entropy": 0, "n_tokens": len(self.structural), "n_semantic": 0,
            "plateau": False, "spike_quartile": -1, "spike_token_idx": -1,
            "quartile_entropies": [0, 0, 0, 0],
            "first_token_entropy": 0, "first3_mean": 0, "first5_mean": 0,
            "first10_mean": 0, "first10_max": 0, "first10_std": 0,
            "early_slope": 0, "early_vs_rest": 0, "first_to_max_ratio": 0,
            "q_slope": 0, "q_curvature": 0, "q_argmax": -1,
            "trajectory_ds": [],
            "phi_first": 0, "phi_first10_mean": 0, "phi_mean": 0,
            "margin_first": 0, "margin_mean": 0,
            "struct_ent_mean": 0, "struct_ent_std": 0,
            "think_boundary": 0, "think_frac": 0.0,
            "plateau_start_quartile": -1, "spike_relative_pos": 0,
        }
        for name in ("full_ent", "mass1", "mass5", "mass20", "tail_mass",
                     "kl_step", "kl_cent", "margin", "kl_uniform",
                     "surprisal", "rank"):
            empty.update(_series_summary(name, []))
        for name in ("ent", "phi", "margin", "kl_step", "kl_cent", "full_ent"):
            empty[f"think_{name}_mean"] = 0
            empty[f"think_{name}_std"] = 0
            empty[f"answer_{name}_mean"] = 0
            empty[f"answer_{name}_std"] = 0
        empty.update(_shape_features(empty))
        return empty


# ─── Math helpers ─────────────────────────────────────────────────────────────

def _series_summary(name: str, xs: List[float]) -> Dict[str, float]:
    if not xs:
        return {f"{name}_{s}": 0 for s in
                ("mean", "max", "min", "std", "first", "f5_mean", "f10_mean",
                 "f10_max", "slope", "early_vs_rest", "late_minus_early")}
    n = len(xs)
    mean = sum(xs) / n
    var = sum((v - mean) ** 2 for v in xs) / n
    first10 = xs[:10]
    m10 = sum(first10) / len(first10)
    k = len(first10)
    if k >= 3:
        xbar = (k - 1) / 2.0
        num = sum((i - xbar) * (v - m10) for i, v in enumerate(first10))
        den = sum((i - xbar) ** 2 for i in range(k))
        slope = num / den if den else 0.0
    else:
        slope = 0.0
    rest = xs[10:]
    half = n // 2
    return {
        f"{name}_mean": mean, f"{name}_max": max(xs), f"{name}_min": min(xs),
        f"{name}_std": var ** 0.5, f"{name}_first": xs[0],
        f"{name}_f5_mean": sum(xs[:5]) / min(5, n),
        f"{name}_f10_mean": m10, f"{name}_f10_max": max(first10),
        f"{name}_slope": slope,
        f"{name}_early_vs_rest": (m10 - sum(rest) / len(rest)) if rest else 0.0,
        f"{name}_late_minus_early": (
            sum(xs[half:]) / (n - half) - sum(xs[:half]) / half) if half else 0.0,
    }


def _shape_features(ent: Dict[str, Any]) -> Dict[str, float]:
    q = ent.get("quartile_entropies") or []
    if len(q) < 4:
        return {}
    q = list(q[:4])
    m = ent.get("mean_entropy") or 0.0
    out = {
        "q1": q[0], "q2": q[1], "q3": q[2], "q4": q[3],
        "q_slope_shape": q[3] - q[0],
        "q_early_drop": q[0] - q[1],
        "q_curvature_shape": (q[0] + q[3]) - (q[1] + q[2]),
        "q_argmax_shape": float(max(range(4), key=lambda i: q[i])),
        "q_range": max(q) - min(q),
        "q_monotone_down": float(sum(1 for i in range(3) if q[i + 1] <= q[i])),
    }
    if m:
        out["q1_over_mean"] = q[0] / m
        out["q4_over_mean"] = q[3] / m
    t = ent.get("trajectory_ds") or []
    if len(t) >= 6:
        n_t = len(t)
        diffs = [t[i + 1] - t[i] for i in range(n_t - 1)]
        downs = sum(1 for dd in diffs if dd < 0)
        out["mono_down_frac"] = downs / len(diffs)
        signs = [1 if dd > 0 else (-1 if dd < 0 else 0) for dd in diffs]
        nz = [x for x in signs if x]
        out["osc_sign_changes"] = float(
            sum(1 for i in range(len(nz) - 1) if nz[i] != nz[i + 1]))
        out["osc_rate"] = (out["osc_sign_changes"] / (len(nz) - 1)
                           if len(nz) > 1 else 0.0)
        tv = sum(abs(dd) for dd in diffs)
        net = abs(t[-1] - t[0])
        out["path_ratio"] = (tv / net) if net > 1e-9 else 0.0
        out["total_variation"] = tv
        ranks = sorted(range(n_t), key=lambda i: t[i])
        rank_of = [0] * n_t
        for pos, i in enumerate(ranks):
            rank_of[i] = pos
        mean_r = (n_t - 1) / 2.0
        num = sum((i - mean_r) * (rank_of[i] - mean_r) for i in range(n_t))
        den = sum((i - mean_r) ** 2 for i in range(n_t))
        out["trend_rho"] = (num / den) if den else 0.0
        base = sum(t) / n_t
        sd_t = (sum((v - base) ** 2 for v in t) / n_t) ** 0.5
        thr = base + sd_t
        out["n_spikes"] = float(sum(1 for i in range(1, n_t)
                                    if t[i] > thr >= t[i - 1]))
        out["spike_height"] = (max(t) - base) / sd_t if sd_t > 1e-9 else 0.0
        out["late_vs_early_half"] = (sum(t[n_t // 2:]) / (n_t - n_t // 2)
                                     - sum(t[:n_t // 2]) / (n_t // 2))
    return out


def permutation_p(group_a: List[float], group_b: List[float],
                  iters: int = PERM_ITERS, seed: int = PERM_SEED) -> float:
    """Two-sided permutation p-value for a difference in means."""
    if len(group_a) < 3 or len(group_b) < 3:
        return 1.0
    observed = abs(sum(group_a) / len(group_a) - sum(group_b) / len(group_b))
    pool = list(group_a) + list(group_b)
    n_a = len(group_a)
    rng = random.Random(seed)
    hits = 0
    for _ in range(iters):
        rng.shuffle(pool)
        a = pool[:n_a]
        b = pool[n_a:]
        diff = abs(sum(a) / len(a) - sum(b) / len(b))
        if diff >= observed:
            hits += 1
    return (hits + 1) / (iters + 1)


def cohens_d(group_a: List[float], group_b: List[float]) -> float:
    n_a, n_b = len(group_a), len(group_b)
    if n_a < 2 or n_b < 2:
        return 0.0
    pooled = group_a + group_b
    mean = sum(pooled) / len(pooled)
    var = sum((x - mean) ** 2 for x in pooled) / len(pooled)
    sd = var ** 0.5
    if sd == 0:
        return 0.0
    return (sum(group_a) / n_a - sum(group_b) / n_b) / sd


def min_detectable_effect(n_ok: int, n_fail: int) -> Optional[float]:
    if n_ok < 2 or n_fail < 2:
        return None
    return MDE_CONST * ((1.0 / n_ok + 1.0 / n_fail) ** 0.5)


def benjamini_hochberg(p_values: List[float],
                       alpha: float = ALPHA) -> Tuple[List[float], List[bool]]:
    m = len(p_values)
    if m == 0:
        return [], []
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [1.0] * m
    running = 1.0
    for rank in range(m - 1, -1, -1):
        i = order[rank]
        val = p_values[i] * m / (rank + 1)
        running = min(running, val)
        adjusted[i] = min(1.0, running)
    return adjusted, [a < alpha for a in adjusted]


# ─── Structural blacklist ─────────────────────────────────────────────────────

def build_structural_blacklist(llm) -> frozenset:
    """Scan the model's vocab once. Returns frozenset of structural token IDs
    (whitespace, punctuation, special tokens). These are excluded from the
    semantic entropy series so formatting tokens don't dilute the signal."""
    structural = set()
    n_vocab = llm.n_vocab()
    for tid in range(n_vocab):
        try:
            piece = llm.token_to_piece(tid)
        except Exception:
            continue
        s = piece.rstrip("\x00")
        if not s.strip():
            structural.add(tid)
            continue
        if s in ("</s>", "<|end|>", "<|eot_id|>", "<end_of_turn>",
                 "<|im_start|>", "<|im_end|>", "<|tool_call|>", "",
                 "", "", "<|begin_of_text|>", "<|end_of_text|>"):
            structural.add(tid)
            continue
        if s.startswith("<|") and s.endswith("|>"):
            structural.add(tid)
            continue
        stripped = s.lstrip()
        if stripped and all(c in _PUNCT_CHARS for c in stripped):
            structural.add(tid)
    return frozenset(structural)


# ─── Code extraction and testing ──────────────────────────────────────────────

def strip_thinking(text: str) -> str:
    """Strip thinking blocks from model output."""
    _THINK_END = "\u003c\u002fthink\u003e"
    _THINK_START = "\u003cthink\u003e"
    thinking_end = text.find(_THINK_END)
    if thinking_end != -1:
        return text[thinking_end + len(_THINK_END):].strip()
    if text.lstrip().startswith(_THINK_START):
        return text.strip()
    return text.strip()


def extract_code(text: str) -> str:
    """Extract Python code from model output (strip thinking, find code block)."""
    text = strip_thinking(text)
    m = re.search(r'```(?:python)?\s*\n(.*?)```', text, re.DOTALL)
    if m:
        return m.group(1).strip()
    # No code block — try the whole text
    return text


def test_function_code(code: str, task: Dict, tmpdir: str) -> Tuple[int, int, List[str]]:
    """Write code to file, import, run eval tests. Returns (passed, total, failures)."""
    fp = os.path.join(tmpdir, task["filename"])
    with open(fp, "w", encoding="utf-8") as f:
        f.write(code)
    mod = task["filename"].replace(".py", "")
    runner = f"import sys\nsys.path.insert(0,r'{tmpdir}')\nfrom {mod} import *\n"
    passed = 0
    total = len(task["tests"])
    failures = []
    for expr, expected in task["tests"]:
        test_code = (runner + f"\nresult = repr({expr})\nexpected = repr({expected})"
                     f"\nassert result == expected, f'got {{result}}, expected {{expected}}'\nprint('PASS')\n")
        try:
            r = subprocess.run([sys.executable, "-c", test_code],
                               capture_output=True, text=True, timeout=10,
                               cwd=tmpdir)
        except subprocess.TimeoutExpired:
            failures.append(f"{expr}: TIMEOUT (10s)")
            continue
        if r.returncode == 0:
            passed += 1
        else:
            failures.append(f"{expr}: {r.stderr.strip()[:150]}")
    return passed, total, failures


# ─── Signal scan ──────────────────────────────────────────────────────────────

def scan_signals(probe_results: List[Dict]) -> Tuple[List[Dict], Optional[Dict]]:
    """Test every numeric entropy statistic, then correct for having tested them all."""
    usable = [r for r in probe_results if r.get("entropy", {}).get("n_semantic", 0) > 5]
    if len(usable) < 6:
        return [], None
    # Merge recorded statistics with derived shape features
    merged = []
    for r in usable:
        e = dict(r["entropy"])
        e.update(_shape_features(r["entropy"]))
        merged.append({"ok": r["ok"], "entropy": e})
    usable = merged
    keys = sorted(k for k, v in usable[0]["entropy"].items()
                  if isinstance(v, (int, float)) and not isinstance(v, bool))
    rows = []
    for k in keys:
        ok = [r["entropy"][k] for r in usable if r["ok"] and k in r["entropy"]]
        fail = [r["entropy"][k] for r in usable if not r["ok"] and k in r["entropy"]]
        if len(ok) < 3 or len(fail) < 3:
            continue
        d = cohens_d(ok, fail)
        if d == 0.0:
            continue
        rows.append({
            "signal": k, "cohens_d": round(d, 3),
            "direction": "high=good" if d > 0 else "high=bad",
            "p_raw": round(permutation_p(ok, fail), 4),
            "n_ok": len(ok), "n_fail": len(fail),
        })
    if not rows:
        return [], None
    adj, survives = benjamini_hochberg([r["p_raw"] for r in rows])
    for r, a, sv in zip(rows, adj, survives):
        r["p_adjusted"] = round(a, 4)
        r["survives_correction"] = bool(sv)
        r["nominally_significant"] = r["p_raw"] < ALPHA
    rows.sort(key=lambda r: r["p_raw"])
    winners = [r for r in rows
               if r["survives_correction"] and abs(r["cohens_d"]) >= 0.2]
    best = max(winners, key=lambda r: abs(r["cohens_d"])) if winners else None
    return rows, best


# ─── Generation ───────────────────────────────────────────────────────────────

def generate(llm, prompt: str, preset: Dict, blacklist: frozenset,
             is_thinking: bool, think_marker_ids: set = None) -> Tuple[str, Dict, float]:
    """Generate with entropy trajectory capture."""
    max_tokens = 4096 if is_thinking else 1200
    sys_prompt = "You are a Python coding assistant. Write clean, correct code."
    full_prompt = (f"<|im_start|>system\n{sys_prompt}<|im_end|>\n"
                   f"<|im_start|>user\n{prompt}<|im_end|>\n"
                   f"<|im_start|>assistant\n")
    stop = ["<|im_end|>", "<|eot_id|>", "<end_of_turn>", "<|end|>", "</s>"]
    collector = EntropyTrajectory(blacklist, timeout=GEN_TIMEOUT_S,
                                  think_marker_ids=think_marker_ids)
    kwargs = {
        "max_tokens": max_tokens,
        "temperature": preset["temp"], "top_p": preset["top_p"],
        "top_k": preset["top_k"], "stop": stop, "echo": False,
        "logits_processor": [collector],
    }
    if preset.get("min_p", 0) > 0:
        kwargs["min_p"] = preset["min_p"]
    if preset.get("repeat_penalty", 1.0) != 1.0:
        kwargs["repeat_penalty"] = preset["repeat_penalty"]
    if preset.get("presence_penalty", 0) > 0:
        kwargs["presence_penalty"] = preset["presence_penalty"]
    t0 = time.time()
    try:
        r = llm.create_completion(full_prompt, **kwargs)
    except GenTimeout:
        elapsed = time.time() - t0
        print(f"    [timeout] generation aborted after {elapsed:.0f}s", flush=True)
        return "", collector.stats(), elapsed
    except Exception:
        kwargs.pop("presence_penalty", None)
        try:
            r = llm.create_completion(full_prompt, **kwargs)
        except Exception as e:
            elapsed = time.time() - t0
            print(f"    [error] {e}", flush=True)
            return "", collector.stats(), elapsed
    elapsed = time.time() - t0
    text = r["choices"][0]["text"]
    return text, collector.stats(), elapsed


def normalize_model_label(model_path: str) -> str:
    """Make a clean, searchable label from a GGUF filename.

    Removes the .gguf extension, strips redundant vendor prefixes
    (e.g. 'Qwen_Qwen3...' -> 'Qwen3...'), and replaces dots/odd
    separators with underscores so the result filename is safe.
    """
    name = os.path.basename(model_path)
    name = re.sub(r'(?i)\.gguf$', '', name)
    # Strip a redundant vendor prefix like Qwen_Qwen3, Meta_Llama, etc.
    name = re.sub(r'(?i)^(Qwen|Meta|Microsoft|IBM|NVIDIA|Nemotron|Google)_(Qwen|Llama|Phi|Granite|Nemotron|Gemma)',
                  r'\2', name)
    # Replace dots with underscores (e.g. granite-4.1 -> granite-4_1)
    name = name.replace('.', '_')
    return name


def build_prompt(task: Dict, no_think: bool = False) -> str:
    suffix = "\n/no_think" if no_think else ""
    return (f"Task: {task['desc']}{suffix}\n\n"
            f"Write {task['filename']} with the function {task['func_name']}. "
            f"Output only the code in a ```python block.")


# ─── Upload ───────────────────────────────────────────────────────────────────

def try_upload(results: List[Dict], scan_rows: List[Dict],
               best: Optional[Dict], model_label: str, upload_url: str) -> bool:
    """Offer opt-in upload. Returns True if uploaded, False otherwise."""
    if not upload_url:
        return False
    print("\n" + "=" * 70)
    print("OPT-IN DATA UPLOAD")
    print("=" * 70)
    print("""
This tool can upload your results to the public evidence corpus at:
  {url}

What gets sent:
  - Model filename and quant label (parsed from filename)
  - Per-task 16-point downsampled entropy trajectory + pass/fail
  - Signal scan results (which signals survived, d values, p values)
  - Timestamp

What does NOT get sent:
  - NO prompts or task descriptions (standard public tasks only)
  - NO generated code
  - NO user identity or account info
  - NO IP address (the server does not log it)

This helps map which models have signals and which don't, so the next
person with your model doesn't have to run this themselves.
""".format(url=upload_url))

    try:
        answer = input("Upload results to the public corpus? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = "n"
    if answer not in ("y", "yes"):
        print("Skipped. Your results stay local.")
        return False

    # Build the payload — only entropy trajectories and pass/fail, no code
    payload = {
        "model_label": model_label,
        "timestamp": int(time.time()),
        "n_tasks": len(results),
        "n_ok": sum(1 for r in results if r["ok"]),
        "n_fail": sum(1 for r in results if not r["ok"]),
        "per_task": [
            {
                "task_id": r["task_id"],
                "ok": r["ok"],
                "n_semantic": r["entropy"].get("n_semantic", 0),
                "trajectory_ds": r["entropy"].get("trajectory_ds", []),
                "think_frac": r["entropy"].get("think_frac", 0),
                "think_boundary": r["entropy"].get("think_boundary", 0),
            }
            for r in results
        ],
        "scan_top10": [
            {"signal": r["signal"], "d": r["cohens_d"], "p_raw": r["p_raw"],
             "p_adj": r["p_adjusted"], "survives": r["survives_correction"]}
            for r in scan_rows[:10]
        ],
        "best_signal": ({"signal": best["signal"], "d": best["cohens_d"],
                         "direction": best["direction"],
                         "p_adj": best["p_adjusted"]}
                        if best else None),
    }
    try:
        import urllib.request
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            upload_url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                print("Uploaded. Thank you — your data strengthens the public corpus.")
                return True
            else:
                print(f"Upload failed (HTTP {resp.status}). Results stay local.")
                return False
    except Exception as e:
        print(f"Upload failed ({e}). Results stay local.")
        return False


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Probe your local GGUF model for entropy-based wrongness signals.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python probe.py --model qwen3-8b-Q5_K_M.gguf
  python probe.py --model qwen3-4b-instruct.gguf --temp 0.7 --top-p 0.8
  python probe.py --model qwen3-8b.gguf --thinking --temp 0.6
  python probe.py --model granite-4.1-3b.gguf --repeats 2

The full calibration kit (170 signals, intervention routing, live proxy):
  https://github.com/charlesdvaught-hash/calibration-kit-public
""")
    parser.add_argument("--model", required=False, help="Path to GGUF model file")
    parser.add_argument("--validate", action="store_true",
                        help="Validate the task bank (run references against tests) and exit")
    parser.add_argument("--temp", type=float, default=0.7, help="Temperature (default 0.7)")
    parser.add_argument("--top-p", type=float, default=0.8, help="Top-p (default 0.8)")
    parser.add_argument("--top-k", type=int, default=20, help="Top-k (default 20)")
    parser.add_argument("--min-p", type=float, default=0.0, help="Min-p (default 0)")
    parser.add_argument("--repeat-penalty", type=float, default=1.0,
                        help="Repetition penalty (default 1.0 = off)")
    parser.add_argument("--presence-penalty", type=float, default=0.0,
                        help="Presence penalty (default 0)")
    parser.add_argument("--thinking", action="store_true",
                        help="Model is a thinking model (uses 4096 max_tokens, strips thinking blocks)")
    parser.add_argument("--no-think", action="store_true",
                        help="Append /no_think to prompts (for Qwen3 dual-mode models) to disable thinking")
    parser.add_argument("--repeats", type=int, default=1,
                        help="Repeat each task N times (default 1; use 2+ for stochastic models)")
    parser.add_argument("--target-failures", type=int, default=DEFAULT_TARGET_FAILURES,
                        help=f"Stop after collecting this many failures (default {DEFAULT_TARGET_FAILURES}). "
                             f"Tasks are sorted easy→hard; strong models skip easy wins, "
                             f"weak models stop early once enough failures are collected.")
    parser.add_argument("--holdout", type=int, default=30,
                        help="After early stop, run up to N more tasks as holdout to test "
                             "whether the discovered signal predicts out-of-sample (default 30). "
                             "Set to 0 to disable.")
    parser.add_argument("--holdout-rerank", type=int, default=0,
                        help="After the holdout prediction, generate up to N extra samples "
                             "for each task (same temperature) and keep the one with the "
                             "best signal value. Set to 0 to disable, 2 for best-of-3.")
    parser.add_argument("--no-early-stop", action="store_true",
                        help="Run all tasks even after reaching target failures (use with --repeats for full sweeps)")
    parser.add_argument("--n-gpu-layers", type=int, default=-1,
                        help="GPU layers for llama-cpp-python (default -1 = all)")
    parser.add_argument("--upload-url", default=DEFAULT_UPLOAD_URL,
                        help="Opt-in upload endpoint (set PROBE_UPLOAD_URL env var or pass here)")
    parser.add_argument("--no-upload", action="store_true",
                        help="Skip the upload prompt entirely")
    args = parser.parse_args()

    if args.validate:
        print("Validating task bank (running reference implementations)...")
        ok = validate()
        if ok:
            print(f"\nAll {len(FUNCTION_TASKS)} tasks validated successfully.")
            sys.exit(0)
        else:
            print("\nSome tasks FAILED validation. Check the output above.")
            sys.exit(1)

    if not args.model:
        parser.error("--model is required (or use --validate to check the task bank)")

    model_path = args.model
    if not os.path.isfile(model_path):
        print(f"Error: model file not found: {model_path}")
        sys.exit(1)

    model_label = normalize_model_label(model_path)

    print("=" * 70)
    print("CALIBRATION PROBE — Signal Discovery Tool")
    print("=" * 70)
    print(f"Model:  {model_label}")
    print(f"Tasks:  {len(ALL_TASKS)} coding tasks (easy→hard)")
    print(f"Repeats: {args.repeats}")
    if not args.no_early_stop:
        print(f"Early stop: after {args.target_failures} failures")
    else:
        print(f"Early stop: disabled (running all tasks)")
    print(f"Thinking mode: {'yes' if args.thinking else 'no'}")
    print(f"Sampling: temp={args.temp} top_p={args.top_p} top_k={args.top_k}")
    if args.presence_penalty > 0:
        print(f"  presence_penalty={args.presence_penalty}")
    if args.repeat_penalty != 1.0:
        print(f"  repeat_penalty={args.repeat_penalty}")
    print()

    # Load model
    print("Loading model...", flush=True)
    try:
        from llama_cpp import Llama
    except ImportError:
        print("Error: llama-cpp-python not installed.")
        print("  pip install llama-cpp-python numpy")
        sys.exit(1)
    try:
        import numpy  # noqa: F401
    except ImportError:
        print("Error: numpy not installed.")
        print("  pip install numpy")
        sys.exit(1)

    t0 = time.time()
    llm = Llama(model_path=model_path, n_gpu_layers=args.n_gpu_layers,
                n_ctx=4096, verbose=False)
    print(f"Model loaded in {time.time() - t0:.1f}s", flush=True)

    # Build structural blacklist
    print("Building structural token blacklist...", flush=True)
    blacklist = build_structural_blacklist(llm)
    print(f"  {len(blacklist)} structural tokens excluded from semantic series",
          flush=True)

    # Resolve thinking marker
    think_marker_ids = None
    if args.thinking:
        try:
            ids = llm.tokenize("\u003c\u002fthink\u003e".encode("utf-8"),
                               add_bos=False)
            if len(ids) == 1:
                think_marker_ids = set(ids)
                print(f"  Thinking marker resolved to token id {ids[0]}",
                      flush=True)
            else:
                print("  Warning: think-close tag is multi-token — "
                      "think_boundary will not be available", flush=True)
        except Exception:
            pass

    preset = {
        "temp": args.temp, "top_p": args.top_p, "top_k": args.top_k,
        "min_p": args.min_p, "repeat_penalty": args.repeat_penalty,
        "presence_penalty": args.presence_penalty,
    }

    # Run tasks
    results = []
    n_tasks = len(ALL_TASKS) * args.repeats
    early_stop = not args.no_early_stop
    target_failures = args.target_failures
    failure_count = 0
    stopped_early = False
    print(f"\nRunning up to {n_tasks} generations...", flush=True)
    if early_stop:
        print(f"(will stop after {target_failures} failures)\n", flush=True)
    else:
        print(flush=True)
    t_start = time.time()

    for repeat in range(args.repeats):
        for i, task in enumerate(ALL_TASKS):
            idx = repeat * len(ALL_TASKS) + i + 1
            prompt = build_prompt(task, args.no_think)
            print(f"  [{idx}/{n_tasks}] {task['id']:<28} ", end="", flush=True)
            text, entropy, elapsed = generate(
                llm, prompt, preset, blacklist, args.thinking, think_marker_ids)
            code = extract_code(text)
            with tempfile.TemporaryDirectory() as td:
                passed, total, failures = test_function_code(code, task, td)
            ok = (passed == total)
            results.append({
                "task_id": task["id"], "ok": ok,
                "passed": passed, "total": total,
                "entropy": entropy, "elapsed": elapsed,
            })
            status = "PASS" if ok else f"FAIL ({passed}/{total})"
            print(f"{status}  ({elapsed:.1f}s, {entropy.get('n_semantic', 0)} sem tokens)",
                  flush=True)
            if not ok:
                failure_count += 1
                if early_stop and failure_count >= target_failures:
                    print(f"\n  Early stop: reached {target_failures} failures. "
                          f"Stopping after {len(results)} generations.", flush=True)
                    stopped_early = True
                    break
        if stopped_early:
            break

    total_elapsed = time.time() - t_start
    n_ok = sum(1 for r in results if r["ok"])
    n_fail = sum(1 for r in results if not r["ok"])

    print(f"\n{'=' * 70}")
    print(f"RESULTS: {n_ok} passed, {n_fail} failed, {total_elapsed:.0f}s total"
          + (f" (stopped early at {target_failures} failures)" if stopped_early else ""))
    print(f"{'=' * 70}\n")

    # Scan signals
    print("Scanning candidate signals...", flush=True)
    scan_rows, best = scan_signals(results)

    if scan_rows:
        print(f"\n  Top 10 signals (of {len(scan_rows)} tested):")
        print(f"  {'Signal':<30} {'d':>7} {'p_raw':>8} {'p_adj':>8} {'survives':>9}")
        print(f"  {'-' * 30} {'-' * 7} {'-' * 8} {'-' * 8} {'-' * 9}")
        for r in scan_rows[:10]:
            surv = "YES" if r["survives_correction"] else "no"
            print(f"  {r['signal']:<30} {r['cohens_d']:>+7.3f} "
                  f"{r['p_raw']:>8.4f} {r['p_adjusted']:>8.4f} {surv:>9}")

    # Verdict
    print(f"\n{'=' * 70}")
    print("VERDICT")
    print(f"{'=' * 70}\n")

    if best:
        mde = min_detectable_effect(n_ok, n_fail)
        print(f"  SIGNAL FOUND: {best['signal']}")
        print(f"  Cohen's d:    {best['cohens_d']:+.3f} ({best['direction']})")
        print(f"  p (adjusted): {best['p_adjusted']:.4f}")
        print(f"  This means: when '{best['signal']}' is {'high' if best['cohens_d'] > 0 else 'low'},")
        print(f"  the model is {'more' if best['cohens_d'] > 0 else 'less'} likely to be correct.")
        print(f"\n  This is a fingerprint on THIS model on THESE {len(ALL_TASKS)} demo tasks.")
        print(f"  It is NOT a universal signal for this model, and it is NOT a")
        print(f"  signal for your actual tasks. It only shows the method can find")
        print(f"  a pattern on this example task distribution.")
        print(f"\n  The full calibration kit learns the signal on your real tasks")
        print(f"  and turns it into a live gate:")
        print(f"    https://github.com/charlesdvaught-hash/calibration-kit-public")
    elif n_fail < 3:
        print(f"  NO FAILURES TO ANALYZE.")
        print(f"  Your model passed all {n_ok} tasks. Either it's very good at")
        print(f"  these tasks, or the task bank is too easy for it.")
        print(f"  Try --repeats 3 with a higher --temp to generate more variance.")
    elif n_fail < 8:
        mde = min_detectable_effect(n_ok, n_fail)
        print(f"  UNDERPOWERED: only {n_fail} failures.")
        if mde:
            print(f"  Minimum detectable effect: d >= {mde:.2f}")
            print(f"  (A 'large' effect is d=0.8. This run can only detect")
            print(f"   effects {'larger than' if mde > 0.8 else 'at about'} that size.)")
        print(f"\n  Try --repeats 2 or --repeats 3 to get more failures.")
        print(f"  No signal found does NOT mean no signal exists —")
        print(f"  it means this run couldn't see one.")
    else:
        mde = min_detectable_effect(n_ok, n_fail)
        print(f"  NO SIGNAL FOUND.")
        print(f"  Scanned {len(scan_rows)} candidate signals, none survived")
        print(f"  Benjamini-Hochberg correction at alpha={ALPHA}.")
        if mde:
            print(f"  Minimum detectable effect: d >= {mde:.2f}")
        print(f"\n  This is an honest null result on these {len(ALL_TASKS)} demo tasks.")
        print(f"  Some models genuinely don't have a usable entropy signal on")
        print(f"  the demo task distribution. The full kit learns a signal on")
        print(f"  your own tasks and checks for repair-routing rules that may")
        print(f"  still be useful even without a gate:")
        print(f"    https://github.com/charlesdvaught-hash/calibration-kit-public")

    # ─── Holdout: test the signal on unseen tasks near the cusp ──────────────
    holdout_results = []
    if best and args.holdout > 0 and stopped_early:
        # The holdout tasks are the next N tasks in the bank after early stop.
        # These are naturally near the model's difficulty cusp — harder than
        # the tasks it breezed through, but not impossibly hard.
        n_train = len(results)
        holdout_start_idx = n_train  # next task in ALL_TASKS
        holdout_tasks = ALL_TASKS[holdout_start_idx:holdout_start_idx + args.holdout]

        if not holdout_tasks:
            print(f"\n{'=' * 70}")
            print("HOLDOUT")
            print(f"{'=' * 70}\n")
            print("  No holdout tasks available (ran past end of bank).")
        else:
            print(f"\n{'=' * 70}")
            print(f"HOLDOUT: testing signal '{best['signal']}' on {len(holdout_tasks)} unseen tasks")
            print(f"{'=' * 70}\n")

            # Compute signal values for training set to find the decision threshold.
            # We use the midpoint between the mean of pass-group and fail-group
            # as the decision boundary. Direction comes from Cohen's d sign.
            train_signal_vals = []
            for r in results:
                e = dict(r["entropy"])
                e.update(_shape_features(r["entropy"]))
                val = e.get(best["signal"])
                if val is not None:
                    train_signal_vals.append((val, r["ok"]))

            pass_vals = [v for v, ok in train_signal_vals if ok]
            fail_vals = [v for v, ok in train_signal_vals if not ok]
            if pass_vals and fail_vals:
                threshold = (sum(pass_vals) / len(pass_vals)
                             + sum(fail_vals) / len(fail_vals)) / 2.0
            elif pass_vals:
                threshold = sum(pass_vals) / len(pass_vals)
            else:
                threshold = 0.0

            # d > 0 means high signal = more likely correct.
            # Predict pass if signal is on the "good" side of threshold.
            high_is_good = best["cohens_d"] > 0

            print(f"  Signal:     {best['signal']} ({best['direction']})")
            print(f"  Threshold:  {threshold:.4f} (midpoint of pass/fail means)")
            print(f"  Training:   {len(pass_vals)} pass, {len(fail_vals)} fail")
            print()

            correct = 0
            total_h = 0
            for i, task in enumerate(holdout_tasks):
                idx = n_train + i + 1
                prompt = build_prompt(task, args.no_think)
                print(f"  [{idx}] {task['id']:<28} ", end="", flush=True)
                text, entropy, elapsed = generate(
                    llm, prompt, preset, blacklist, args.thinking, think_marker_ids)
                code = extract_code(text)
                with tempfile.TemporaryDirectory() as td:
                    passed, total_t, failures = test_function_code(code, task, td)
                ok = (passed == total_t)

                # Compute signal value for the first holdout attempt
                e = dict(entropy)
                e.update(_shape_features(entropy))
                sig_val = e.get(best["signal"], 0.0)

                # Optional: conditional best-of-N rerank using the discovered signal.
                # If the first sample's signal predicts PASS, we keep it (no extra compute).
                # If it predicts FAIL, we generate N more samples, then compare:
                #   - signal-guided: pick the sample with the best signal value
                #   - random control: pick one of the samples uniformly at random
                # This makes rerank compute proportional to predicted failures,
                # and gives a proper A/B control.
                first_ok = ok
                first_sig = sig_val
                samples = [(sig_val, entropy, code, ok)]
                random_idx = 0
                best_idx = 0
                if args.holdout_rerank > 0:
                    # Predict on first sample
                    if high_is_good:
                        predicted_fail = first_sig < threshold
                    else:
                        predicted_fail = first_sig > threshold

                    if not predicted_fail:
                        # Signal is confident this is a pass — keep first sample
                        pass
                    else:
                        print(f" (predicted FAIL, generating {args.holdout_rerank} extra samples)",
                              end="", flush=True)
                        for _ in range(args.holdout_rerank):
                            text_r, entropy_r, elapsed_r = generate(
                                llm, prompt, preset, blacklist, args.thinking, think_marker_ids)
                            code_r = extract_code(text_r)
                            with tempfile.TemporaryDirectory() as td:
                                passed_r, total_r, _ = test_function_code(code_r, task, td)
                            ok_r = (passed_r == total_r)
                            e_r = dict(entropy_r)
                            e_r.update(_shape_features(entropy_r))
                            sig_val_r = e_r.get(best["signal"], 0.0)
                            samples.append((sig_val_r, entropy_r, code_r, ok_r))

                        # Signal-guided: pick the best signal value
                        if high_is_good:
                            best_idx = max(range(len(samples)), key=lambda i: samples[i][0])
                        else:
                            best_idx = min(range(len(samples)), key=lambda i: samples[i][0])

                        # Random control: pick one uniformly
                        random_idx = random.randrange(len(samples))

                        # Use signal-guided as the chosen sample
                        sig_val, entropy, code, ok = samples[best_idx]
                        print(f"  kept signal sample {best_idx + 1}/{len(samples)}", flush=True)

                # Predict using the threshold on the chosen sample
                if high_is_good:
                    predicted_pass = sig_val >= threshold
                else:
                    predicted_pass = sig_val <= threshold

                prediction = "PASS" if predicted_pass else "FAIL"
                actual = "PASS" if ok else "FAIL"
                hit = predicted_pass == ok
                if hit:
                    correct += 1
                total_h += 1

                holdout_results.append({
                    "task_id": task["id"], "ok": ok,
                    "first_ok": first_ok,
                    "ok_after_rerank": ok if args.holdout_rerank > 0 else None,
                    "random_ok": samples[random_idx][3] if args.holdout_rerank > 0 and len(samples) > 1 else first_ok,
                    "random_idx": random_idx if args.holdout_rerank > 0 and len(samples) > 1 else 0,
                    "signal_value": sig_val,
                    "first_signal_value": first_sig,
                    "predicted_pass": predicted_pass,
                    "correct_prediction": hit,
                    "n_samples": len(samples) if args.holdout_rerank > 0 else 1,
                    "sample_outcomes": [s[3] for s in samples],
                    "sample_signals": [s[0] for s in samples],
                    "selected_idx": best_idx,
                })

                mark = "✓" if hit else "✗"
                if args.holdout_rerank > 0 and len(samples) > 1:
                    control = samples[random_idx][3]
                    print(f"{actual:>4}  signal={sig_val:+.6f}  pred={prediction:>4}  {mark}  "
                          f"(random control: {'PASS' if control else 'FAIL'})")
                else:
                    print(f"{actual:>4}  signal={sig_val:+.6f}  pred={prediction:>4}  {mark}")

            accuracy = correct / total_h if total_h > 0 else 0.0
            # Baseline: always predict the majority class from training
            majority_pass = len(pass_vals) >= len(fail_vals)
            baseline_acc = (sum(1 for h in holdout_results if h["ok"] == majority_pass)
                           / total_h if total_h > 0 else 0.0)

            print(f"\n  Holdout accuracy:   {correct}/{total_h} = {accuracy:.0%}")
            print(f"  Baseline (majority): {baseline_acc:.0%} (always predict "
                  f"{'PASS' if majority_pass else 'FAIL'})")
            print(f"  Lift over baseline:  {accuracy - baseline_acc:+.0%}")

            if args.holdout_rerank > 0:
                first_passes = sum(1 for h in holdout_results if h["first_ok"])
                rerank_passes = sum(1 for h in holdout_results if h["ok"])
                random_passes = sum(1 for h in holdout_results if h.get("random_ok"))
                rescued = sum(1 for h in holdout_results
                              if not h["first_ok"] and h["ok"])
                random_rescued = sum(1 for h in holdout_results
                                     if not h["first_ok"] and h.get("random_ok"))
                worsened = sum(1 for h in holdout_results
                               if h["first_ok"] and not h["ok"])

                # Conditional rerank: count how many tasks triggered extra samples
                reranked_tasks = [h for h in holdout_results if h.get("n_samples", 1) > 1]
                n_reranked = len(reranked_tasks)

                # Did the signal select a passing sample when one existed?
                selectable = [h for h in holdout_results if True in h["sample_outcomes"]]
                selected_passing = sum(
                    1 for h in selectable if h["sample_outcomes"][h["selected_idx"]])
                random_selected_passing = sum(
                    1 for h in selectable if h["sample_outcomes"][h["random_idx"]])
                rerank_precision = (selected_passing / len(selectable)
                                    if selectable else 0.0)
                random_precision = (random_selected_passing / len(selectable)
                                    if selectable else 0.0)

                # Expected random from distribution (n_pass / n_total)
                random_hits = 0.0
                for h in selectable:
                    n_pass = sum(h["sample_outcomes"])
                    n_total = len(h["sample_outcomes"])
                    random_hits += n_pass / n_total
                expected_random = random_hits / len(selectable) if selectable else 0.0

                # Average samples per task (conditional rerank lowers this)
                avg_samples = sum(h["n_samples"] for h in holdout_results) / total_h

                print(f"\n  Conditional best-of-(1+{args.holdout_rerank}) rerank results:")
                print(f"    Tasks reranked (predicted FAIL):   {n_reranked}/{total_h}")
                print(f"    Avg samples per holdout task:      {avg_samples:.2f}")
                print(f"    First-sample pass rate:            {first_passes}/{total_h} ({first_passes/total_h:.0%})")
                print(f"    Signal-guided pass rate:           {rerank_passes}/{total_h} ({rerank_passes/total_h:.0%})")
                print(f"    Random control pass rate:          {random_passes}/{total_h} ({random_passes/total_h:.0%})")
                print(f"    Failures rescued by signal:        {rescued}")
                print(f"    Failures rescued by random:        {random_rescued}")
                print(f"    Passes lost:                       {worsened}")
                print(f"    Net change vs first sample:        {rescued - worsened:+d}")
                print(f"    Tasks with at least one PASS:      {len(selectable)}")
                print(f"    Signal picked a PASS among them:   {selected_passing}/{len(selectable)} ({rerank_precision:.0%})")
                print(f"    Random picked a PASS among them:   {random_selected_passing}/{len(selectable)} ({random_precision:.0%})")
                print(f"    Expected random (n_pass/n_total):  {expected_random:.0%}")

                if rerank_precision > random_precision:
                    print(f"\n  ✓ The signal-selected sample did better than random on demo tasks.")
                    print(f"    Signal rescued {rescued} failure(s); random rescued {random_rescued}.")
                    print(f"    This is evidence the calibration method can choose better")
                    print(f"    answers on example tasks. The kit does this on your tasks.")
                elif rerank_precision == random_precision:
                    print(f"\n  ~ Signal and random performed equally. The signal did not "
                          f"consistently identify the better sample on these demo tasks.")
                else:
                    print(f"\n  ✗ Signal did worse than random. The signal may be too noisy "
                          f"at this threshold for reranking on these demo tasks.")
            elif accuracy > baseline_acc:
                print(f"\n  ✓ The signal generalized to unseen tasks near the cusp.")
                print(f"    This is evidence the calibration has practical value:")
                print(f"    it can predict failures before the test runs.")
            elif accuracy == baseline_acc:
                print(f"\n  ~ The signal matched baseline. No practical benefit shown")
                print(f"    on this holdout set, though the signal may still be real.")
            else:
                print(f"\n  ✗ The signal did worse than baseline on holdout.")
                print(f"    It may be overfit to the training tasks, or the effect")
                print(f"    is too small to predict individual outcomes.")
    elif args.holdout > 0 and not best:
        print(f"\n  (Holdout skipped: no signal found to test.)")
    elif args.holdout > 0 and not stopped_early:
        print(f"\n  (Holdout skipped: early stop was not triggered. "
              f"Use --target-failures to enable holdout testing.)")

    # Upload
    if not args.no_upload and args.upload_url:
        try_upload(results, scan_rows, best, model_label, args.upload_url)
    elif not args.no_upload and not args.upload_url:
        print("\n  (Set PROBE_UPLOAD_URL or pass --upload-url to contribute")
        print("   results to the public evidence corpus.)")

    # Save local results
    outfile = f"probe_{model_label}_results.json"
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump({
            "model_label": model_label,
            "preset": preset,
            "thinking": args.thinking,
            "n_ok": n_ok, "n_fail": n_fail,
            "stopped_early": stopped_early,
            "target_failures": target_failures,
            "scan_rows": scan_rows[:20],
            "best_signal": best,
            "holdout": holdout_results if holdout_results else None,
            "per_task": [
                {"task_id": r["task_id"], "ok": r["ok"],
                 "passed": r["passed"], "total": r["total"],
                 "n_semantic": r["entropy"].get("n_semantic", 0),
                 "trajectory_ds": r["entropy"].get("trajectory_ds", []),
                 "think_frac": r["entropy"].get("think_frac", 0)}
                for r in results
            ],
        }, f, indent=2)
    print(f"\n  Results saved to {outfile}")

    # Print contribution instructions
    print(f"\n{'─' * 70}")
    print(f"  CONTRIBUTE TO THE PUBLIC DATASET")
    print(f"{'─' * 70}")
    if not args.no_upload and args.upload_url:
        pass  # Already prompted above
    else:
        print(f"  Three ways to share your results:")
        print(f"\n  1. GitHub PR (recommended — auto-syncs to HF dataset on merge):")
        print(f"     python contribute.py {outfile}")
        print(f"     # Or: fork the repo, add to submissions/, open a PR")
        print(f"\n  2. HuggingFace PR (opens a PR directly on the HF dataset):")
        print(f"     pip install huggingface_hub")
        print(f"     python upload_to_hf.py {outfile} --token hf_YOUR_TOKEN")
        print(f"     # Get a token at huggingface.co/settings/tokens")
        print(f"\n  3. Cloudflare Worker (faster, but needs a deployed worker):")
        print(f"     Set PROBE_UPLOAD_URL or pass --upload-url")
        print(f"\n  What gets shared: entropy trajectories + pass/fail + signal scan.")
        print(f"  What does NOT: no code, no prompts, no identity, no IP.")


if __name__ == "__main__":
    main()



