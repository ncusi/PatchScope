#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Usage: {script_name} <diff_path> <result_path>
Annotates single diff and saves result as json

"""
import codecs
import json
import sys
from collections import defaultdict
from pathlib import Path

from unidiff import PatchSet

from hunk_annotation.annotate import PatchFile


def annotate_single_diff(diff_path):
    patch = defaultdict(lambda: defaultdict(list))
    with codecs.open(diff_path, "r", encoding="utf-8") as diff:
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
