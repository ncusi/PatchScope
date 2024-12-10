# -*- coding: utf-8 -*-
"""Test cases for 'src/diffannotator/annotate.py' module"""
import copy
import re
from pathlib import Path
from textwrap import dedent

import pytest
import unidiff
from pygments.lexers import CLexer
from pygments.token import Token

from diffannotator.annotate import (split_multiline_lex_tokens, line_ends_idx,
                                    group_tokens_by_line, front_fill_gaps, deep_update,
                                    clean_text, line_is_comment, line_is_empty, annotate_single_diff,
                                    Bug, BugDataset, AnnotatedPatchedFile, AnnotatedHunk, AnnotatedPatchSet,
                                    line_is_whitespace)
from diffannotator.utils.git import GitRepo, DiffSide, ChangeSet
from .conftest import count_pm_lines

# Example code to be tokenized
example_C_code = r'''
 /**
  * brief       Calculate approximate memory requirements for raw encoder
  *
  */

  int i = 1; /* an int */
'''

# example patch from "Listing 1. Patch for bug Closure-40"
# in https://doi.org/10.1109/SANER.2018.8330203,
# taken in turn from Defects4J
# https://program-repair.org/defects4j-dissection/#!/bug/Closure/40
# https://github.com/rjust/defects4j/blob/master/framework/projects/Closure/patches/40.src.patch
example_patch_java = r'''
diff --git a/src/com/google/javascript/jscomp/NameAnalyzer.java b/src/com/google/javascript/jscomp/NameAnalyzer.java
index 6e9e470..088a993 100644
--- a/src/com/google/javascript/jscomp/NameAnalyzer.java
+++ b/src/com/google/javascript/jscomp/NameAnalyzer.java
@@ -632,9 +632,11 @@ final class NameAnalyzer implements CompilerPass {
         Node nameNode = n.getFirstChild();
         NameInformation ns = createNameInformation(t, nameNode, n);
         if (ns != null && ns.onlyAffectsClassDef) {
-          JsName name = getName(ns.name, true);
+          JsName name = getName(ns.name, false);
+          if (name != null) {
           refNodes.add(new ClassDefiningFunctionNode(
               name, n, parent, parent.getParent()));
+          }
         }
       }
     }
'''


@pytest.fixture()
def example_patchset_java() -> unidiff.PatchSet:
    """PatchSet created from Closure-40 source diff in Defects4J dataset"""
    return unidiff.PatchSet(example_patch_java)


def test_line_ends_idx():
    text = "1st line\n2nd line\n3rd then empty\n\n5th line\n"
    pos_list = line_ends_idx(text)

    assert "1st line\n" == text[0:pos_list[0]]
    assert "2nd line\n" == text[pos_list[0]:pos_list[1]]


def test_front_fill_gaps():
    input_data = {1: '1',
                  4: '4',
                  5: '5',
                  7: '7'}
    expected = {1: '1', 2: '1', 3: '1',
                4: '4',
                5: '5', 6: '5',
                7: '7'}

    actual = front_fill_gaps(input_data)

    assert actual == expected


def test_deep_update():
    original = {
        "level1": {
            "level2": {"level3-A": 0, "level3-B": 1}
        },
        "list": list('abc'),
    }
    dictionary = copy.deepcopy(original)
    update = {
        "level1": {
            "level2": {"level3-B": 10}
        },
        "list": list('de'),
        "new key": 1,
    }
    result = deep_update(dictionary, update)

    # check a few cases
    assert result["level1"]["level2"]["level3-A"] == 0, \
        "deeply nested 'level3-A' value kept"
    assert result["level1"]["level2"]["level3-B"] == 10, \
        "deeply nested 'level3-B' value updated"
    assert result["list"] == list('abcde'), \
        "list value 'list' extended"
    assert "new key" in result and result["new key"] == 1, \
        "new key 'new key' added"


def test_clean_text():
    text_to_clean = "some text with * / \\ \t and\nnew\nlines     and  spaces"
    expected = "some text with andnewlines and spaces"
    actual = clean_text(text_to_clean)

    assert actual == expected


def test_post_image_from_diff():
    file_path = 'tests/test_dataset/tqdm-1/c0dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff'
    patch = unidiff.PatchSet.from_filename(file_path, encoding='utf-8')
    assert len(patch) == 1, "there is only one changed file in patch set"
    hunk = patch[0][0]

    line_type = unidiff.LINE_TYPE_ADDED
    source = ''.join([str(line.value) for line in hunk
                      # unexpectedly, there is no need to check for unidiff.LINE_TYPE_EMPTY
                      if line.line_type in {line_type, unidiff.LINE_TYPE_CONTEXT}])

    # end first line with \ to avoid the empty line
    expected = dedent("""\
            if isinstance(iterable, np.ndarray):
                return tqdm_class(np.ndenumerate(iterable),
                                  total=total or len(iterable), **tqdm_kwargs)
        return enumerate(tqdm_class(iterable, **tqdm_kwargs), start)


    def _tzip(iter1, *iter2plus, **tqdm_kwargs):""")

    assert source == expected, "post image matches expected result"


def test_annotate_single_diff():
    # code patch
    file_path = 'tests/test_dataset/tqdm-1/c0dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff'
    patch = annotate_single_diff(file_path, missing_ok=False,
                                 ignore_diff_parse_errors=False,
                                 ignore_annotation_errors=False)['changes']
    # check file data
    expected_language_data = {
        'language': 'Python',
        'purpose': 'programming',
        'type': 'programming',
    }
    changed_file_name = 'tqdm/contrib/__init__.py'
    assert changed_file_name in patch, \
        "correct file name is used in patch data"
    assert expected_language_data.items() <= patch[changed_file_name].items(), \
        "correct language is being detected"
    # check line data
    # - check number of`changes
    assert len(patch[changed_file_name]['-']) == 1, \
        "there is only one removed line (one changed line)"
    assert len(patch[changed_file_name]['+']) == 1, \
        "there is only one added line (one changed line)"
    # - check content of changes
    actual_removed = ''.join([x[2]  # value, that is, text_fragment
                              for x in patch[changed_file_name]['-'][0]['tokens']])
    expected_removed = "    return enumerate(tqdm_class(iterable, start, **tqdm_kwargs))\n"
    assert actual_removed == expected_removed, \
        "data from '-' annotation matches expected removed line"
    actual_added = ''.join([x[2]  # value, that is, text_fragment
                            for x in patch[changed_file_name]['+'][0]['tokens']])
    expected_added = "    return enumerate(tqdm_class(iterable, **tqdm_kwargs), start)\n"
    assert actual_added == expected_added, \
        "data from '+' annotation matches expected added line"
    # - check position in hunk
    hunk_line_no = 3   # there are usually 3 context lines before the change
    hunk_line_no += 1  # first there is single removed line (for one changed line)
    assert patch[changed_file_name]['-'][0]['id'] + 1 == hunk_line_no, \
        "index of line in hunk for '-' annotation matches the patch"
    hunk_line_no += 1  # then there is single added line (for one changed line)
    assert patch[changed_file_name]['+'][0]['id'] + 1 == hunk_line_no, \
        "index of line in hunk for '+' annotation matches the patch"
    # - check type
    assert patch[changed_file_name]['-'][0]['type'] == 'code', \
        "removed line is marked as code"
    assert patch[changed_file_name]['+'][0]['type'] == 'code', \
        "added line is marked as code"

    # documentation patch
    file_path = 'tests/test_dataset/unidiff-1/3353080f357a36c53d21c2464ece041b100075a1.diff'
    patch = annotate_single_diff(file_path, missing_ok=False,
                                 ignore_diff_parse_errors=False,
                                 ignore_annotation_errors=False)['changes']
    # check file data
    assert 'README.rst' in patch, \
        "correct file name is used in patch data"
    assert patch['README.rst']['purpose'] == 'documentation', \
        "'README.rst' file purpose is documentation"
    # check line data
    pre_image_lines = patch['README.rst']['-']
    post_image_lines = patch['README.rst']['+']
    assert all([line['purpose'] == 'documentation'
                for line in pre_image_lines]), \
        "all pre-image lines of 'README.rst' are marked as documentation"
    assert all([line['purpose'] == 'documentation'
                for line in post_image_lines]), \
        "all post-image lines of 'README.rst' are marked as documentation"

    file_path = 'tests/test_dataset/empty.diff'
    patch = annotate_single_diff(file_path, missing_ok=False,
                                 ignore_diff_parse_errors=False,
                                 ignore_annotation_errors=False)
    assert patch == {}, "empty result on an empty diff"

    file_path = 'tests/test_dataset/this_patch_does_not_exist.diff'
    with pytest.raises(FileNotFoundError):
        annotate_single_diff(file_path, missing_ok=False)


def test_hunk_sizes_and_spreads(example_patchset_java: unidiff.PatchSet):
    patched_file = example_patchset_java[0]
    #print(f"{example_patchset_java=}")
    #print(f"{patched_file=}")
    #print(f"{patched_file[0]=}")

    annotated_patched_file = AnnotatedPatchedFile(patched_file)
    annotated_hunk = AnnotatedHunk(annotated_patched_file, patched_file[0], 0)
    hunk_result, hunk_info = annotated_hunk.compute_sizes_and_spreads()
    #print(f"{annotated_hunk.hunk=}")
    #print(f"{annotated_hunk.hunk.section_header=}")
    #from pprint import pprint
    #pprint(hunk_result)
    #pprint(hunk_info)

    # Listing 1 shows an example of patch
    # with one modified line (line 635), two non-paired removed
    # lines (the old 636 and 639 lines), and none non-paired added
    # line. By summing these lines, we have the metric patch size
    # in number of lines, which in the example is 3 lines.
    #
    # But patch on Listing 1 in Sobreira et al. 2018 is *wrong*,
    # so the above is also wrong.  Asserted values are instead
    # computed by hand (for given patch, copied from Defects4J)
    assert hunk_result['n_mod'] == 1, "one modified line"
    assert hunk_result['n_rem'] == 0, "no non-paired removed lines"
    assert hunk_result['n_add'] == 2, "two non-paired added lines"
    assert hunk_result['patch_size'] == 3, "patch size is 3 lines"
    assert hunk_result['n_groups'] == 2, "two groups of changed lines (chunks)"
    assert hunk_result['n_hunks'] == 1, "analyzed only 1 hunk"

    assert hunk_result['n_lines_all'] == 12, "12 lines in hunk, excluding hunk header"
    assert hunk_result['n_lines_added'] == 3, "3 lines beginning with '+' in hunk"
    assert hunk_result['n_lines_removed'] == 1, "1 line beginning with '-' in hunk"

    assert hunk_result['spread_inner'] == 2, "2 context lines between 2 groups (chunks)"

    # diff header of example_diff_java:
    # @@ -632,9 +632,11 @@ final class NameAnalyzer implements CompilerPass {
    assert hunk_info['hunk_start'] == (632, 632), "'hunk_start' agrees with hunk header info"
    assert hunk_info['hunk_end'] == (632+9-1, 632+11-1), "'hunk_end' agrees with hunk header info"

    assert hunk_info['groups_start'] == (635, 635), \
        "'groups_start': hunk start same line in pre-/post-image, first group includes -/+"
    assert hunk_info['groups_end'] == (635, 639), \
        "'groups_end': there was only single '-' line, last group had only '+'"
    assert hunk_info['type_first'] == '-', "first changed line is '-' line"
    assert hunk_info['type_last'] == '+', "last changed line is '+' line"


def test_simple_patchset_sizes_and_spreads(example_patchset_java: unidiff.PatchSet):
    patched_file = example_patchset_java[0]
    #print(f"{example_patchset_java=}")
    #print(f"{patched_file=}")
    #print(f"{patched_file[0]=}")

    annotated_patched_file = AnnotatedPatchedFile(patched_file)
    #print(f"{annotated_patched_file=}")

    patched_file_result = annotated_patched_file.compute_sizes_and_spreads()
    #from pprint import pprint
    #pprint(patched_file_result)

    # there is only one hunk, so we need to test only that which
    # was not tested by test_hunk_sizes_and_spreads() test
    assert patched_file_result['n_files'] == 1, "analyzed only 1 patched file"


def test_misc_patched_files_sizes_and_spreads():
    file_path = 'tests/test_dataset/tqdm-1/c0dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff'
    patch = unidiff.PatchSet.from_filename(file_path, encoding='utf-8')
    patched_file = AnnotatedPatchedFile(patch[0])
    result = patched_file.compute_sizes_and_spreads()

    # computed by hand
    assert result['n_mod'] == 1, "one modified line"
    assert result['n_rem'] == 0, "no non-paired removed lines"
    assert result['n_add'] == 0, "no non-paired added lines"
    assert result['patch_size'] == 1, "patch size is 1 modified line"
    assert result['n_groups'] == 1, "1 groups of changed lines (chunks)"
    assert result['n_hunks'] == 1, "1 hunk in patched file"
    assert result['spread_inner'] == 0, "there is only 1 group, so there is no inner sep"

    file_path = 'tests/test_dataset/unidiff-1/3353080f357a36c53d21c2464ece041b100075a1.diff'
    patch = unidiff.PatchSet.from_filename(file_path, encoding='utf-8')
    patched_file = AnnotatedPatchedFile(patch[0])
    result = patched_file.compute_sizes_and_spreads()

    # computed by hand
    assert result['n_mod'] == 2, "2 modified lines"
    assert result['n_rem'] == 0, "no non-paired removed lines"
    assert result['n_add'] == 0, "no non-paired added lines"
    assert result['patch_size'] == 2, "patch size is 2 modified line"
    assert result['n_groups'] == 1, "1 groups of changed lines (chunks)"
    assert result['n_hunks'] == 1, "1 hunk in patched file"
    assert result['spread_inner'] == 0, "there is only 1 group, so there is no inner sep"

    file_path = 'tests/test_dataset_structured/keras-10/patches/c1c4afe60b1355a6c0e83577791a0423f37a3324.diff'
    patch = unidiff.PatchSet.from_filename(file_path, encoding='utf-8')
    #print(f"{patch[0]=}")
    #print(f"expected span = {45 + 13 + (3 + 3 + 1) + 8 + (1) =}")
    #print(f"inter-hunk spaces = {(480-436+1, 497-485+1, 521-514+1)}")
    patched_file = AnnotatedPatchedFile(patch[0])
    result = patched_file.compute_sizes_and_spreads()
    #from pprint import pprint
    #pprint(result)

    # computed by hand
    assert result['n_mod'] == 12, "12 modified lines"
    assert result['n_rem'] == 7, "7 non-paired removed lines"
    assert result['n_add'] == 13, "13 non-paired added lines"
    assert result['patch_size'] == 32, "patch size is 32 modified, removed, and added lines"
    assert result['n_hunks'] == 4, "4 hunks in patched file"
    assert result['n_groups'] == 1+1+4+2, "8 groups of changed lines in 4 hunks total"
    assert result['spread_inner'] == 0+0+(3+3+1)+1, "sum of inner separations for 4 hunks"

    # computed by hand, helped by expanding inter-hunk space in commit diff fully, at
    # https://github.com/keras-team/keras/commit/c1c4afe60b1355a6c0e83577791a0423f37a3324
    assert result['groups_spread'] == 45 + 13 + (3 + 3 + 1) + 8 + (1), \
        "computed groups spread matches hand count, test_dataset_structure, patch[0]"

    file_path = 'tests/test_dataset_annotated/CVE-2021-21332/patches/e54746bdf7d5c831eabe4dcea76a7626f1de73df.diff'
    patch = unidiff.PatchSet.from_filename(file_path, encoding='utf-8')
    #print(f"{patch[2]=}")
    #print(f"expected span = {(1)+7+7+(6)+16+9=}")
    #print(f"inter-hunk spaces = {(251-236+1,261-253+1)}")
    patched_file = AnnotatedPatchedFile(patch[2])
    result = patched_file.compute_sizes_and_spreads()
    #from pprint import pprint
    #pprint(result)
    assert result['groups_spread'] == (1) + 7 + 7 + (6) + 16 + 9, \
        "computed groups spread matches hand count, test_dataset_annotated, patch[2]"

    #print(f"\n{patch[6]=}")
    #print(f"expected span     = {16=}")
    #print(f"inter-hunk spaces = {(686-671+1)=}=={(695-680+1)=}")
    patched_file = AnnotatedPatchedFile(patch[6])
    result = patched_file.compute_sizes_and_spreads()
    #from pprint import pprint
    #pprint(result)
    assert result['groups_spread'] == 16, \
        "computed groups spread matches hand count, test_dataset_annotated, patch[6]"


def test_misc_patchsets_sizes_and_spreads():
    # checking only complex, multi-file patches (diffs)
    file_path = 'tests/test_dataset_structured/keras-10/patches/c1c4afe60b1355a6c0e83577791a0423f37a3324.diff'
    patch_set = AnnotatedPatchSet.from_filename(file_path, encoding='utf-8')
    result = patch_set.compute_sizes_and_spreads()
    #print(f"{file_path=}")
    #print(f"{patch_set=}, {patch_set.patch_set=}")
    #from pprint import pprint
    #pprint(result)
    assert result['n_files'] == 2, "there were 2 changed files in patch"

    file_path = 'tests/test_dataset_annotated/CVE-2021-21332/patches/e54746bdf7d5c831eabe4dcea76a7626f1de73df.diff'
    patch_set = AnnotatedPatchSet.from_filename(file_path, encoding='utf-8')
    result = patch_set.compute_sizes_and_spreads()
    #print(f"{file_path=}")
    #print(f"{patch_set=}, {patch_set.patch_set=}")
    #from pprint import pprint
    #pprint(result)
    assert result['n_files'] == 12, "there were 12 changed files in patch"

    file_path = 'tests/test_dataset/tensorflow/87de301db14745ab920d7e32b53d926236a4f2af.diff'
    patch_set = AnnotatedPatchSet.from_filename(file_path, encoding='utf-8')
    diff_metadata = patch_set.compute_sizes_and_spreads()
    changes_data  = patch_set.process(sizes_and_spreads=False)['changes']

    assert len(changes_data) == diff_metadata['n_files'] + diff_metadata['n_file_renames'], \
        f"number of files matches between 'changes' and 'diff_metadata' for {file_path}"

    total_m, total_p = count_pm_lines(changes_data)

    ## DEBUG
    #print(f"TOTAL: {total_m=}, {total_p=}, {total_p+total_m=}")
    #print(f"META:  "
    #      f"'n_rem'={diff_metadata['n_rem']}, 2*'n_mod'={2*diff_metadata['n_mod']}, 'n_add'={diff_metadata['n_add']}")
    #print(f"META:  "
    #      f"'n_rem'+'n_mod'={diff_metadata['n_rem'] + diff_metadata['n_mod']}, ",
    #      f"'n_mod'+'n_add'={diff_metadata['n_mod'] + diff_metadata['n_add']}")
    #print(f"META:  "
    #      f"'n_rem'+2*'n_mod'+'n_add'={diff_metadata['n_rem'] + 2*diff_metadata['n_mod'] + diff_metadata['n_add']}")

    assert total_m == diff_metadata['n_rem'] + diff_metadata['n_mod'], \
        f"number of '-' lines matches between 'changes' and 'diff_metadata' in {file_path}"
    assert total_p == diff_metadata['n_add'] + diff_metadata['n_mod'], \
        f"number of '+' lines matches between 'changes' and 'diff_metadata' in {file_path}"
    assert total_m + total_p == diff_metadata['n_rem'] + 2*diff_metadata['n_mod'] + diff_metadata['n_add'], \
        f"number of -/+ lines matches between 'changes' and 'diff_metadata' in {file_path}"


@pytest.mark.parametrize("line_type", [unidiff.LINE_TYPE_REMOVED, unidiff.LINE_TYPE_ADDED])
def test_AnnotatedPatchedFile(line_type):
    # code patch
    file_path = 'tests/test_dataset_structured/keras-10/patches/c1c4afe60b1355a6c0e83577791a0423f37a3324.diff'

    # create AnnotatedPatchedFile object
    patch_set = unidiff.PatchSet.from_filename(file_path, encoding="utf-8")
    patched_file_no_source = AnnotatedPatchedFile(patch_set[0])    # .add_sources*() modify object
    patched_file_with_source = AnnotatedPatchedFile(patch_set[0])

    # add contents of pre-image and post-image
    files_path = Path('tests/test_dataset_structured/keras-10/files')  # must agree with `file_path`
    src_path = files_path / 'a' / Path(patched_file_with_source.source_file).name
    dst_path = files_path / 'b' / Path(patched_file_with_source.target_file).name
    patched_file_with_source = patched_file_with_source.add_sources_from_files(src_path, dst_path)

    src_text = src_path.read_text(encoding="utf-8")
    dst_text = dst_path.read_text(encoding="utf-8")
    assert patched_file_with_source.image_for_type('-') == src_text, \
        "image_for_type returns pre-image for '-'"
    assert patched_file_with_source.image_for_type('+') == dst_text, \
        "image_for_type returns post-image for '+'"

    src_tokens = patched_file_with_source.tokens_for_type(line_type)
    #print(f"{src_tokens[:2]}")
    assert src_tokens is not None, \
        f"tokens_for_type returns something for '{line_type}'"
    assert len(list(src_tokens)) > 0, \
        f"tokens_for_type returns non-empty iterable of tokens for '{line_type}'"

    first_hunk = AnnotatedHunk(patched_file=patched_file_no_source,
                               hunk=patched_file_no_source.patched_file[0],
                               hunk_idx=0)
    first_hunk_from_sourced = AnnotatedHunk(patched_file=patched_file_with_source,
                                            hunk=patched_file_with_source.patched_file[0],
                                            hunk_idx=0)

    bare_hunk_data = first_hunk.process()
    srcd_hunk_data = first_hunk_from_sourced.process()  # should use sources
    # DEBUG
    #print(f"{bare_hunk_data=}")
    #print(f"{srcd_hunk_data=}")
    bare_hunk_tokens = {line_data['id']: line_data['tokens'] for line_data
                        in bare_hunk_data['keras/engine/training_utils.py'][line_type]}
    srcd_hunk_tokens = {line_data['id']: line_data['tokens'] for line_data
                        in srcd_hunk_data['keras/engine/training_utils.py'][line_type]}
    # DEBUG
    #print(f"{bare_hunk_tokens=}")
    #print(f"{srcd_hunk_tokens=}")
    bare_tokens_renumbered = {
        i: bare_hunk_tokens[idx] for i, idx in zip(range(len(bare_hunk_tokens)), bare_hunk_tokens.keys())
    }
    bare_lines_renumbered = {
        i: "".join([tok[2] for tok in tokens])
        for i, tokens in bare_tokens_renumbered.items()
    }
    # DEBUG
    #print(f"{bare_tokens_renumbered=}")
    #print(f"{bare_lines_renumbered=}")
    srcd_tokens_renumbered = {
        i: val for i, val in enumerate(srcd_hunk_tokens.values())
    }
    srcd_lines_renumbered = {
        i: "".join([tok[2] for tok in tokens])
        for i, tokens in enumerate(srcd_hunk_tokens.values())
    }
    # DEBUG
    #print(f"{srcd_tokens_renumbered=}")
    #print(f"{srcd_lines_renumbered=}")

    tokens_for_hunk = patched_file_with_source.hunk_tokens_for_type(line_type, first_hunk_from_sourced.hunk)
    hunk_tokens = first_hunk_from_sourced.tokens_for_type(line_type)
    assert tokens_for_hunk == hunk_tokens, \
        f"Both ways of getting tokens for {'removed' if line_type == '-' else 'added'} lines return same result"
    # DEBUG
    #print(f"{tokens_for_hunk=}")
    tokens_renumbered = {
        i: tokens_for_hunk[idx] for i, idx in zip(range(len(tokens_for_hunk)), tokens_for_hunk.keys())
    }
    lines_renumbered = {
        i: "".join([tok[2] for tok in tokens])
        for i, tokens in tokens_renumbered.items()
    }
    # DEBUG
    #print(f"{tokens_renumbered=}")
    #print(f"{lines_renumbered=}")
    # DEBUG
    #tokens_sel = patched_file_with_source.tokens_range_for_type('-', 432-1, 7)
    #for k, v in tokens_sel.items():
    #    print(f"{k}: {v}")

    assert bare_lines_renumbered == lines_renumbered, \
        "AnnotatedHunk.process() and AnnotatedPatchedFile.hunk_tokens_for_type() give the same lines"
    assert bare_tokens_renumbered != tokens_renumbered, \
        "lexing pre-image from diff is not the same as lexing whole pre-image file, in this case"

    assert srcd_lines_renumbered == lines_renumbered, \
        "AnnotatedHunk.process() with source and AnnotatedPatchedFile.hunk_tokens_for_type() give the same lines"
    assert srcd_tokens_renumbered == tokens_renumbered, \
        "AnnotatedHunk.process() with source and AnnotatedPatchedFile.hunk_tokens_for_type() give the same tokens"


def test_AnnotatedPatchSet_binary_files_differ():
    # .......................................................................
    # patch with binary files
    file_path = 'tests/test_dataset_structured/scrapy-11/patches/9de6f1ca757b7f200d15e94840c9d431cf202276.diff'

    patch_set = AnnotatedPatchSet.from_filename(file_path,
                                                missing_ok=False, ignore_diff_parse_errors=False)

    sizes_and_spreads = patch_set.compute_sizes_and_spreads()
    #print(f"{sizes_and_spreads=}")
    assert sizes_and_spreads['n_binary_files'] == 2, 'changes to 2 binary files'
    assert sizes_and_spreads['n_files'] == 4, "changes to 2 files"

    result = patch_set.process()
    result = result['changes']
    #print(f"{result=}")
    for pm in ['+', '-']:
        assert pm not in result['/dev/null'], \
            f"no '{pm}' lines for /dev/null"
        assert pm not in result['tests/sample_data/compressed/unexpected-eof-output.txt'], \
            f"no '{pm}' lines for binary file with *.txt extension"
        assert pm not in result['tests/sample_data/compressed/unexpected-eof.gz'], \
            f"no '{pm}' lines for binary file with *.gz extension"


def test_Bug_from_dataset():
    # code patch
    file_path = Path('tests/test_dataset/tqdm-1/c0dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff')

    bug = Bug.from_dataset('tests/test_dataset', 'tqdm-1',
                           patches_dir="", annotations_dir="")
    assert file_path.name in bug.patches, \
        "retrieved annotations for the single *.diff file"
    assert len(bug.patches) == 1, \
        "there was only 1 patch file for a bug"
    assert "tqdm/contrib/__init__.py" in bug.patches[file_path.name]['changes'], \
        "there is expected changed file in a bug patch"


def test_Bug_from_dataset_with_fanout():
    # code patch
    file_path = 'tests/test_dataset_fanout/tqdm-1/c0/dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff'

    commit_id = '/'.join(Path(file_path).parts[-2:])
    bug = Bug.from_dataset('tests/test_dataset_fanout', 'tqdm-1',
                           patches_dir="", annotations_dir="", fan_out=True)

    assert commit_id in bug.patches, \
        "retrieved annotations for the single *.diff file"
    assert len(bug.patches) == 1, \
        "there was only 1 patch file for a bug"
    assert "tqdm/contrib/__init__.py" in bug.patches[commit_id]['changes'], \
        "there is expected changed file in a bug patch"


def test_Bug_from_patchset():
    file_path = 'tests/test_dataset/tqdm-1/c0dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff'
    patch = unidiff.PatchSet.from_filename(file_path, encoding='utf-8')

    commit_id = Path(file_path).stem
    bug = Bug.from_patchset(patch_id=commit_id, patch_set=patch)
    assert commit_id in bug.patches, \
        "retrieved annotations for the single patchset"
    assert len(bug.patches) == 1, \
        "there was only 1 patchset for a bug"
    assert "tqdm/contrib/__init__.py" in bug.patches[commit_id]['changes'], \
        "there is expected changed file in a bug patch"

    bug_with_wrong_repo = Bug.from_patchset(patch_id=commit_id, patch_set=patch,
                                            repo=GitRepo('.'))
    assert commit_id in bug_with_wrong_repo.patches, \
        "retrieved annotations for the single patchset (with wrong repo)"
    assert bug.patches == bug_with_wrong_repo.patches, \
        "passing incorrect repo should not change annotations at all"

    bug_with_invalid_repo = Bug.from_patchset(patch_id=commit_id, patch_set=patch,
                                              repo=GitRepo('a/b/c'))
    assert commit_id in bug_with_invalid_repo.patches, \
        "retrieved annotations for the single patchset (with invalid repo)"


def test_Bug_from_changeset():
    # see tests/test_utils_git.py::test_ChangeSet_from_filename
    commit_id = 'c0dcf39b046d1b4ff6de14ac99ad9a1b10487512'
    filename_diff = f'tests/test_dataset/tqdm-1/{commit_id}.diff_with_raw'
    changeset = ChangeSet.from_filename(filename_diff, newline='\r\n')

    bug = Bug.from_patchset(patch_id=commit_id, patch_set=changeset)
    assert [commit_id] == list(bug.patches.keys()), \
        "expected commit, and only expected commit, is in bug.patches"
    assert 'commit_metadata' in bug.patches[commit_id], \
        "commit information was extracted from the '--format=raw -p' diff"

    # remove 'commit_metadata' to make further checks easier
    # 'commit_metadata' is checked in another test
    del bug.patches[commit_id]['commit_metadata']

    # DEBUG
    #print(f"{bug=}")
    #print(f"{len(bug.patches[commit_id])=}")
    #print(f"{bug.patches[commit_id].keys()=}")

    files_changed = ['tqdm/contrib/__init__.py', 'tqdm/tests/tests_contrib.py']

    # DEBUG
    #for f in files_changed:
    #    f_data = bug.patches[commit_id][f]
    #    print(f"{f}: lang={f_data['language']}, type={f_data['type']}, purpose={f_data['purpose']}")
    #    for pm in ['-', '+']:
    #        for line_data in f_data[pm]:
    #            line = "".join([tok[2] for tok in line_data['tokens']])
    #            print(f"  {pm}:{line_data['id']}:type={line_data['type']}, purpose={line_data['purpose']}:{line}",
    #                  end="")  # line includes trailing '\n' (usually)

    assert sorted(files_changed) == sorted(bug.patches[commit_id]['changes'].keys()), \
        "expected files were changed in changeset"
    for changed_file in files_changed:
        assert {
            'language': 'Python',
            'type': 'programming',
        }.items() <= bug.patches[commit_id]['changes'][changed_file].items(), \
            f"language of '{changed_file}' matches expectations"
    assert bug.patches[commit_id]['changes']['tqdm/contrib/__init__.py']['purpose'] == 'programming', \
        "__init__.py file in contrib/ purpose is 'programming'"
    assert bug.patches[commit_id]['changes']['tqdm/tests/tests_contrib.py']['purpose'] == 'test', \
        "test_*.py file in tests/ purpose is 'test'"

    line_types = {}
    for changed_file in files_changed:
        line_types[changed_file] = {
            line_data['type']
            for pm in ['-', '+']
            for line_data in bug.patches[commit_id]['changes'][changed_file][pm]
        }
    #print(f"{line_types=}")
    assert line_types['tqdm/contrib/__init__.py'] <= {'code', 'documentation'}, \
        "types of lines in file which purpose is 'programming' should be 'code' or 'documentation'"


def test_Bug_from_patchset_from_example_repo(example_repo: GitRepo):
    patch = example_repo.unidiff('v2')
    commit_id = example_repo.to_oid('v2')
    if commit_id is None:
        pytest.skip(f"Could not retrieve oid for 'v2' tag from the example repo: {example_repo!r}")

    # DEBUG
    #print(f"{patch=}")
    #file: unidiff.PatchedFile
    #for file in patch:
    #    print(f"- {file=}: {file.source_file} -> {file.target_file}")

    bug = Bug.from_patchset(patch_id=commit_id, patch_set=patch, repo=example_repo)
    # DEBUG
    #print(patch)
    #from pprint import pprint
    #pprint(bug.patches[commit_id])
    # TODO: check that the only warnings are 'No lexer found'/'Unknown file type' in std{out,err}/log

    assert commit_id in bug.patches, \
        "retrieved annotations for the single commit from example repo"
    assert len(bug.patches) == 1, \
        "created Bug object has only 1 patchset (for a single commit)"

    dst_files = example_repo.list_changed_files(commit=commit_id, side=DiffSide.POST)
    assert set(dst_files) <= set(bug.patches[commit_id]['changes'].keys()), \
        "info about every changed file (from post-image side) is in a bug patch from commit"

    diff_stat = example_repo.diff_file_status(commit=commit_id)
    added_files = [ dst_name for (src_name, dst_name), stat in diff_stat.items() if stat == 'A' ]
    #renamed_files = [ f for files, stat in diff_stat.items() if stat == 'R'
    #                  for f in files ]
    renames_list = [ files for files, stat in diff_stat.items() if stat == 'R' ]
    # DEBUG
    #print(f"{added_files=}")
    #print(f"{renames_list=}")
    for f in added_files:
        assert '-' not in bug.patches[commit_id]['changes'][f], \
            f"added file '{f}' has no '-' lines"
    for (s, d) in renames_list:
        assert '+' not in bug.patches[commit_id]['changes'][s], \
            f"the '{s}' pre-commit of renamed file has no '+' lines"
        assert '-' not in bug.patches[commit_id]['changes'][d], \
            f"the '{d}' post-commit of renamed file has no '-' lines"

    # NOTE: there is no way to check if sources were retrieved, except for mocking,
    # because AnnotatedPatchedFile is created only locally, and Bug stores just annotations


def test_Bug_save(tmp_path: Path):
    bug = Bug.from_dataset('tests/test_dataset_structured', 'keras-10')  # the one with the expected directory structure
    bug.save(tmp_path)

    save_path = tmp_path.joinpath('keras-10', Bug.DEFAULT_ANNOTATIONS_DIR)
    assert save_path.exists(), \
        "directory path to save data exists"
    assert save_path.is_dir(), \
        "directory path to save data is directory"
    assert len(list(save_path.iterdir())) == 1, \
        "there is only one file saved in save directory"
    assert len(list(save_path.glob("*.json"))) == 1, \
        "there is only one JSON file saved in save directory"
    assert save_path.joinpath('c1c4afe60b1355a6c0e83577791a0423f37a3324.v2.json').is_file(), \
        "this JSON file has expected filename"


def test_Bug_save_with_fanout(tmp_path: Path):
    bug = Bug.from_dataset('tests/test_dataset_structured', 'keras-10')  # the one with the expected directory structure
    bug.save(tmp_path, fan_out=True)

    save_path = tmp_path.joinpath('keras-10', Bug.DEFAULT_ANNOTATIONS_DIR)
    assert save_path.joinpath('c1', 'c4afe60b1355a6c0e83577791a0423f37a3324.v2.json').is_file(), \
        "JSON file was saved with fan-out"


def test_BugDataset_from_directory():
    bugs = BugDataset.from_directory('tests/test_dataset_structured')

    assert len(bugs) >= 1, \
        "there is at least one bug in the dataset"
    assert 'keras-10' in bugs, \
        "the bug with 'keras-10' identifier is included in the dataset"
    assert bugs.bug_ids == list(bugs), \
        "iterating over bug identifiers works as expected"

    bug = bugs.get_bug('keras-10')
    assert isinstance(bug, Bug), \
        "get_bug() method returns Bug object"


def test_BugDataset_from_directory_with_fanout():
    bugs = BugDataset.from_directory(dataset_dir='tests/test_dataset_fanout',
                                     patches_dir='', annotations_dir='', fan_out=True)

    bug = bugs.get_bug('tqdm-1')
    assert isinstance(bug, Bug), \
        "get_bug() method returns Bug object"
    assert len(bug.patches) == 1, \
        "there is exactly 1 patch for 'tqdm-1' bug"


# MAYBE: mark that it requires network
@pytest.mark.slow
def test_BugDataset_from_repo(tmp_path: Path):
    # MAYBE: create a global variable in __init__.py
    sha1_re = re.compile(r"^[0-9a-fA-F]{40}$")  # SHA-1 identifier is 40 hex digits long
    # MAYBE: create fixture
    test_repo_url = 'https://github.com/githubtraining/hellogitworld.git'
    repo = GitRepo.clone_repository(
        repository=test_repo_url,
        working_dir=tmp_path,
        make_path_absolute=True,
    )
    if repo is None:
        pytest.skip(f"Could not clone Git repo from {test_repo_url}")
    if repo.count_commits() < 3:
        pytest.skip(f"Less than 3 commits starting from 'HEAD' in {repo.repo}")

    bugs = BugDataset.from_repo(repo, revision_range=('-3', 'HEAD'))

    assert len(bugs) == 3, \
        "we got 3 commit ids we expected from `git log -3 HEAD` in the dataset"
    assert all([re.fullmatch(sha1_re, bug_id)
                for bug_id in bugs.bug_ids]), \
        "all bug ids in the dataset look like SHA-1"
    assert bugs._dataset_path is None, \
        "there is no path to a dataset directory stored in BugDataset"
    assert bugs._patches is not None, \
        "patches data is present in _patches field"
    assert bugs.bug_ids == list(bugs._patches.keys()), \
        "there is 1-to-1 correspondence between bug ids and keys to patch data"

    annotated_data = list(bugs.iter_bugs(sizes_and_spreads=True))

    assert len(annotated_data) == 3, \
        "we got 3 annotated bugs we expected from `git log -3 HEAD`"
    assert all([isinstance(bug, Bug)
                for bug in annotated_data]), \
        "all elements of bugs.get_bugs() are Bug objects"
    assert all([len(bug.patches) == 1 and list(bug.patches.items())[0][0] == bug_id
                for bug_id, bug in zip(bugs.bug_ids, annotated_data)]), \
        "all bugs remember their ids correctly"

    ## DEBUG
    #from rich.pretty import pprint  # OR: from pprint import pprint
    #for patch_data in annotated_data:
    #    pprint(patch_data.patches, max_length=12)

    for i, annotated_patch_data in enumerate(annotated_data, start=1):
        bug_patches = list(annotated_patch_data.patches.values())[0]  # dict with single key, we want value
        diff_metadata = bug_patches['diff_metadata']
        assert len(bug_patches['changes']) == diff_metadata['n_files'] + diff_metadata['n_file_renames'], \
            f"number of files matches between 'changes' and 'diff_metadata' for patchset № {i}"

        total_m, total_p = count_pm_lines(bug_patches['changes'])

        ## DEBUG
        #print(f"{i}: {annotated_patch_data.patches.keys()}")
        #print(f"* {total_m=}, {total_p=}")
        #print(f"* n_rem={diff_metadata['n_rem']}, 2*n_mod={2*diff_metadata['n_mod']}, n_add={diff_metadata['n_add']}")

        assert total_m + total_p == diff_metadata['n_rem'] + 2*diff_metadata['n_mod'] + diff_metadata['n_add'], \
            f"number of -/+ lines matches between 'changes' and 'diff_metadata' for patchset № {i}"


def test_line_callback_trivial():
    # code patch
    file_path = Path('tests/test_dataset/tqdm-1/c0dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff')

    # trivial callback
    line_type = "any"
    AnnotatedPatchedFile.line_callback = lambda file_purpose, tokens: line_type
    patch = annotate_single_diff(file_path, missing_ok=False,
                                 ignore_diff_parse_errors=False,
                                 ignore_annotation_errors=False)

    # - check file
    changed_file_name = 'tqdm/contrib/__init__.py'
    assert changed_file_name in patch['changes'], \
        "correct file name is used in patch data"
    # - check type
    assert patch['changes'][changed_file_name]['-'][0]['type'] == line_type, \
        f"removed line is marked as '{line_type}' by lambda callback"
    assert patch['changes'][changed_file_name]['+'][0]['type'] == line_type, \
        f"added line is marked as '{line_type}' by lambda callback"

    # use exec
    code_str = f"""return '{line_type}'"""
    callback_code_str = ("def callback_x(file_purpose, tokens):\n" +
                         "  " + "\n  ".join(code_str.splitlines()) + "\n")
    exec(callback_code_str, globals())
    AnnotatedPatchedFile.line_callback = \
        locals().get('callback_x',
                     globals().get('callback_x', None))
    patch = annotate_single_diff(file_path, missing_ok=False,
                                 ignore_diff_parse_errors=False,
                                 ignore_annotation_errors=False)

    assert patch['changes'][changed_file_name]['-'][0]['type'] == line_type, \
        f"removed line is marked as '{line_type}' by self-contained exec callback"
    assert patch['changes'][changed_file_name]['+'][0]['type'] == line_type, \
        f"added line is marked as '{line_type}' by self-contained exec callback"


def test_line_callback_whitespace():
    # code patch
    file_path = Path('tests/test_dataset_structured/keras-10/patches/c1c4afe60b1355a6c0e83577791a0423f37a3324.diff')

    # complex callback, untyped
    def detect_all_whitespace_line(_file_purpose, tokens):
        if len(tokens) == 0:
            return "empty"
        elif all([token_type in Token.Text.Whitespace or
                  token_type in Token.Text and text_fragment.isspace()
                  for _, token_type, text_fragment in tokens]):
            return "whitespace"
        else:
            return None

    AnnotatedPatchedFile.line_callback = detect_all_whitespace_line
    patch = annotate_single_diff(file_path, missing_ok=False,
                                 ignore_diff_parse_errors=False,
                                 ignore_annotation_errors=False)

    changed_file_name = 'keras/engine/training_utils.py'
    assert changed_file_name in patch['changes'], \
        f"there is '{changed_file_name}' file used in patch data"
    assert any([elem['type'] == 'whitespace'
                for elem in patch['changes'][changed_file_name]['-']]), \
        f"at least one whitespace only line in pre-image of '{changed_file_name}'"
    assert any([elem['type'] == 'whitespace'
                for elem in patch['changes'][changed_file_name]['+']]), \
        f"at least one whitespace only line in post-image of '{changed_file_name}'"

    # define callback using string
    callback_code = dedent("""\
    # this could be written using ternary conditional operator
    if len(tokens) == 1 and tokens[0][2] == '\\n':
        return 'empty'
    else:
        return None
    """)
    AnnotatedPatchedFile.line_callback = \
        AnnotatedPatchedFile.make_line_callback(callback_code)

    assert AnnotatedPatchedFile.line_callback is not None, \
        "successfully created the callback code from callback string"

    # annotate with the new callback
    patch = annotate_single_diff(file_path, missing_ok=False,
                                 ignore_diff_parse_errors=False,
                                 ignore_annotation_errors=False)

    assert any([elem['type'] == 'empty'
                for elem in patch['changes'][changed_file_name]['-']]), \
        f"at least one empty line in pre-image of '{changed_file_name}'"
    assert any([elem['type'] == 'empty'
                for elem in patch['changes'][changed_file_name]['+']]), \
        f"at least one empty line in post-image of '{changed_file_name}'"


class TestCLexer:
    # Create a lexer instance
    lexer = CLexer()

    def test_splitting_tokens(self):
        # iterable of (index, token_type, value), where `index` is the starting
        # position of the token within the input text; value might consist
        # of multiple lines
        tokens_unprocessed = self.lexer.get_tokens_unprocessed(example_C_code)
        tokens_split = split_multiline_lex_tokens(tokens_unprocessed)

        # we need list for further analysis, not a generator
        tokens_split = list(tokens_split)

        for index, token_type, text_fragment in tokens_split:
            assert text_fragment.count('\n') <= 1, \
                "each text_fragment has at most one newline"

        for i, elem in enumerate(tokens_split):
            idx_curr = elem[0]
            try:
                idx_next = tokens_split[i + 1][0]
            except IndexError:
                idx_next = None

            extracted = example_C_code[idx_curr:idx_next]
            assert extracted == elem[2], \
                f"{i}: index is updated correctly to point to text_fragment"

        assert ''.join([x[2] for x in tokens_split]) == example_C_code, \
            "all text_fragments concatenate to original code"

    def test_group_split_tokens_by_line(self):
        tokens_unprocessed = self.lexer.get_tokens_unprocessed(example_C_code)
        tokens_split = split_multiline_lex_tokens(tokens_unprocessed)

        code_to_group = example_C_code
        tokens_grouped = group_tokens_by_line(code_to_group, tokens_split)

        lines = code_to_group.splitlines(keepends=True)

        assert len(lines) == len(tokens_grouped), \
            "number of lines in code match numbers of token groups"

        for i, line in enumerate(lines):
            assert line == ''.join([x[2] for x in tokens_grouped[i]]), \
                "text_fragments for tokens belonging to a line concatenate to that line"

    def test__line_is__functions(self):
        """Test line_is_comment() and line_is_empty() functions"""
        tokens_unprocessed = self.lexer.get_tokens_unprocessed(example_C_code)
        tokens_split = split_multiline_lex_tokens(tokens_unprocessed)
        tokens_grouped = group_tokens_by_line(example_C_code, tokens_split)

        actual = {
            i: line_is_comment(line_tokens)
            for i, line_tokens in tokens_grouped.items()
        }

        # from pprint import pprint
        # pprint(actual)
        # print("<<<")
        # for i, code_line in enumerate(example_C_code.splitlines(keepends=True)):
        #     print(f"{i:d}: {actual[i]!s:5}: {code_line}", end='')
        # print("<<<")

        assert len(actual) == len(example_C_code.splitlines(keepends=True)), \
            "numbers of lines matches with code"

        # NOTE: these tests *must* be updated it example_C_code changes
        assert not actual[len(actual)-1], \
            "last line in example code is not a comment"
        assert all([v for k, v in actual.items()
                    if (0 < k < len(actual) - 2)]), \
            "all but first line and last 2 lines in example code is a comment"

        actual = {
            i: line_is_empty(line_tokens)
            for i, line_tokens in tokens_grouped.items()
        }

        # print("{{{")
        # for i, code_line in enumerate(example_C_code.splitlines(keepends=False)):
        #     print(f"{i:d}: {actual[i]!s:5}:{code_line}", end=':\n')
        # print("{{{")
        # print(f"{len(actual)=}, {len(actual)-2=}")
        # tokens_list = tokens_grouped[len(actual)-2]
        # print(f"{tokens_list=}")
        # print(f"  {len(tokens_list)=}")
        # print(f"  {tokens_list[0][2]=}")
        # print(f"  {(len(tokens_list) == 1)=}")
        # nl = '\n'
        # print(f"  {(tokens_list[0][2] == nl)=}")

        assert actual[0], \
            "first line in example code is empty"
        assert actual[len(actual)-2], \
            "next to last line in example code is empty"
        assert not any([v for k, v in actual.items()
                        if k != 0 and k != len(actual) - 2]), \
            "all lines but first and next to last line in example code are not empty"

        actual = {
            i: line_is_whitespace(line_tokens)
            for i, line_tokens in tokens_grouped.items()
        }

        #print("{{{")
        #for i, code_line in enumerate(example_C_code.splitlines(keepends=False)):
        #    print(f"{i:d}: {actual[i]!s:5}:{code_line}", end=':\n')
        #print("{{{")

        assert actual[0] and actual[5], \
            "very basic test for whitespace-only lines (and empty lines)"

# end of test_annotate.py
