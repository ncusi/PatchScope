#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Usage: {script_name} <diff_path> <result_path>
Annotates single diff and saves result as json

"""
import codecs
import collections.abc
import json
import re
import sys
from collections import Counter, deque
from collections import defaultdict
from pathlib import Path

from pygments.token import Token
from unidiff import PatchSet, LINE_TYPE_ADDED, LINE_TYPE_REMOVED

from languages import Languages
from lexer import Lexer

LANGUAGES = Languages()
LEXER = Lexer()

global_hunk_counter = Counter()


def map_code_to_tokens(code, tokens):
    tokens = deque(tokens)
    idx_code = [i + 1 for i, ltr in enumerate(code) if ltr == "\n"]
    lines = defaultdict(list)
    for no, idx in enumerate(idx_code):
        while tokens:
            token = tokens.popleft()
            if token[0] < idx:
                lines[no].append(token)
            else:
                tokens.appendleft(token)
                break

    return lines


def fill_gaps_with_previous_value(d):
    if not d:
        return {}

    # Find the minimum and maximum keys
    min_key = min(d.keys())
    max_key = max(d.keys())

    # Create a new dictionary to store the result
    filled_dict = {}

    # Initialize the previous value
    previous_value = None

    # Iterate through the range of keys
    for key in range(min_key, max_key + 1):
        if key in d:
            previous_value = d[key]
        filled_dict[key] = previous_value

    return filled_dict


def deep_update(d, u):
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = deep_update(d.get(k, {}), v)
        else:
            d[k].extend(v)
    return d


TRANSLATION_TABLE = str.maketrans("", "", "*/\\\t\n")


def clean_text(text):
    ret = text.translate(TRANSLATION_TABLE)
    ret = re.sub(r'\s+', ' ', ret)
    return ret


class AnnotateHunk(object):
    refactored_hunks = 0
    refactored_complex_hunks = 0
    all_hunks = 0

    def __init__(self, patch_file, hunk):
        self.patch_file = patch_file
        self.hunk = hunk

        self.patch = defaultdict(lambda: defaultdict(list))

    def get(self):
        hunk = self.hunk

        fsource = self.patch_file.fsource
        ftarget = self.patch_file.ftarget

        if fsource == "/dev/null":
            fout = ftarget
        else:
            fout = fsource

        purpose = self.patch_file.patch[fout]["purpose"]

        changes_types = {}
        changes_lines = {}

        for i, l in enumerate(hunk):
            if l.line_type in ["+", "-"]:
                changes_types[i] = l.line_type
                changes_lines[i] = l.value

                if purpose == "documentation":
                    line_annotation = purpose
                    self.add_annotation(i, ftarget, fsource, changes_types[i], line_annotation, purpose,
                                        [(0, 0, l.value), ])

        if purpose == "documentation":
            return self.patch

        source = ''.join(str(line.value) for line in hunk)

        tokens_list = LEXER.lex(fout, source)

        lines = fill_gaps_with_previous_value(map_code_to_tokens(source, tokens_list))

        max_correct_i = 0
        for i, line in changes_lines.items():
            if i in lines:
                line_annotation = 'documentation' if is_comment(lines[i]) else 'code'
                self.add_annotation(i, ftarget, fsource, changes_types[i], line_annotation, purpose, lines[i])
                max_correct_i = i
            else:  # TODO: bug
                line_annotation = 'documentation' if is_comment(lines[0]) else 'code'
                self.add_annotation(i, ftarget, fsource, changes_types[i], line_annotation, purpose,
                                    lines[max_correct_i])

        code_change = defaultdict(list)

        for ct in ["+", "-"]:
            for hunk in self.patch[ftarget][ct]:
                for token in hunk["tokens"]:
                    code_change[ct].append(clean_text(token[2]))

        prefactoring = 0
        intersection = set(code_change["+"]).intersection(set(code_change["-"]))
        union = set(code_change["+"]).union(set(code_change["-"]))

        if len(intersection) == len(union):
            prefactoring += 1

            print(
                f"Found {prefactoring} refactoring(s) possible refactoring Hunks ref(%)={AnnotateHunk.refactored_hunks / AnnotateHunk.all_hunks}, ref={AnnotateHunk.refactored_hunks}, ref complex={AnnotateHunk.refactored_complex_hunks} all={AnnotateHunk.all_hunks}")
            AnnotateHunk.refactored_hunks += 1

            is_complex_change = False
            for t in intersection:
                if t not in ['', ' ']:
                    is_complex_change = True
            if is_complex_change:
                AnnotateHunk.refactored_complex_hunks += 1

        AnnotateHunk.all_hunks += 1

        return self.patch

    def add_annotation(self, line_no, ftarget, fsource, change_type, line_annotation, purpose, tokens):
        ret = {'id': line_no,
               'type': line_annotation,
               'purpose': purpose,
               'tokens': tokens}

        if change_type == LINE_TYPE_ADDED:
            self.patch[ftarget]["+"].append(ret)
        elif change_type == LINE_TYPE_REMOVED:
            self.patch[fsource]["-"].append(ret)


def is_comment(tokens_list):
    tl = tokens_list

    result = False
    condition = True

    for t in tl:
        if t[1] in Token.Comment:
            result = True
        elif t[1] in Token.Text and t[2].isspace():
            # white space in line is also ok
            result = True
            # pass
        else:
            # other tokens
            condition = False

    if result and condition:
        return True

    return False


class PatchFile(object):
    """Docstring for PatchFile."""

    def __init__(self, file):
        """TODO: to be defined."""

        self.patch = defaultdict(lambda: defaultdict(list))

        self.file = file

        self.fsource = file.source_file
        self.ftarget = file.target_file

        # get the names and drop "a/" and "b/"
        if self.fsource[:2] == "a/":
            self.fsource = file.source_file[2:]
        if self.ftarget[:2] == "b/":
            self.ftarget = file.target_file[2:]

        source_meta_dict = LANGUAGES.annotate(self.fsource)
        self.patch[self.fsource].update(source_meta_dict)

        if self.fsource != self.ftarget:
            target_meta_dict = LANGUAGES.annotate(self.ftarget)
            self.patch[self.ftarget].update(target_meta_dict)

        # Force each file to have changes list -- even if empty changes
        for lt in ["+", "-"]:
            self.patch[self.fsource][lt] = list()
            self.patch[self.ftarget][lt] = list()

    def process(self):
        for hunk in self.file:
            # print(hunk)
            # global_hunk_counter.update(AnnotateHunk(self, hunk).get())

            patch = AnnotateHunk(self, hunk).get()
            # print(patch)
            deep_update(self.patch, patch)
            # print(">>>>>>>>>>>>>>>>")
            # print(patch)
            # print(self.patch)
            # print("END>>>>>>>>>>>>>>>>")
            # self.patch.update(patch)
            # print(self.patch)

            # for line in hunk:
            #     fout, processed_line = AnnotateLine(self, line).get()

            #     if fout:
            #         ltype = line.line_type
            #         self.patch[fout][ltype].append(processed_line)

        return self.patch


def annotate_single_diff(diff_path):
    patch = defaultdict(lambda: defaultdict(list))
    with codecs.open(str(diff_path), "r", encoding="utf-8") as diff:
        try:
            # if True:
            patch_set = PatchSet(diff)
            for file in patch_set:
                patch_file = PatchFile(file)
                patch.update(patch_file.process())
        except Exception as e:
            print("Error", patch_file, e)
            # raise e
    return patch


def main():
    diff_path = Path(sys.argv[1])
    result_path = Path(sys.argv[2])

    result = annotate_single_diff(diff_path)
    print(result)
    with result_path.open(mode='w') as result_file:
        json.dump(result, result_file, indent=4)


if __name__ == '__main__':
    main()
