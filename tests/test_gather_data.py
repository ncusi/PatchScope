# -*- coding: utf-8 -*-
"""Test cases for 'src/diffannotator/gather_data.py' module"""
from collections import Counter
from pathlib import Path

from diffannotator.gather_data import (PurposeCounterResults, AnnotatedBugDataset,
                                       map_diff_to_purpose_dict, map_diff_to_timeline)


def test_AnnotatedBugDataset_with_PurposeCounterResults():
    dataset_path = 'tests/test_dataset_annotated'
    annotated_bug_dataset = AnnotatedBugDataset(dataset_path)
    data = annotated_bug_dataset.gather_data(PurposeCounterResults.create, PurposeCounterResults.default)
    actual_paths = [Path(p).as_posix() for p in data._processed_files]

    assert actual_paths == [
        'tests/test_dataset_annotated/CVE-2021-21332/annotation/e54746bdf7d5c831eabe4dcea76a7626f1de73df.json'
    ]
    assert data._hunk_purposes == Counter({'programming': 5, 'markup': 5, 'other': 2, 'documentation': 1})
    assert data._added_line_purposes == Counter({'programming': 45, 'documentation': 37, 'markup': 13, 'other': 1})
    assert data._removed_line_purposes == Counter({'programming': 25, 'markup': 13})


def test_AnnotatedBugDataset_with_dict_mapping():
    dataset_path = 'tests/test_dataset_annotated'
    annotated_bug_dataset = AnnotatedBugDataset(dataset_path)
    data_dict = annotated_bug_dataset.gather_data_dict(map_diff_to_purpose_dict)

    assert 'CVE-2021-21332' in data_dict
    assert 'e54746bdf7d5c831eabe4dcea76a7626f1de73df.json' in data_dict['CVE-2021-21332']
    assert 'UPGRADE.rst' in data_dict['CVE-2021-21332']['e54746bdf7d5c831eabe4dcea76a7626f1de73df.json']
    assert data_dict['CVE-2021-21332']['e54746bdf7d5c831eabe4dcea76a7626f1de73df.json']['UPGRADE.rst'] == [
        'documentation']


def test_AnnotatedBugDataset_gather_data_list():
    dataset_path = 'tests/test_dataset_annotated'
    annotated_bug_dataset = AnnotatedBugDataset(dataset_path)
    # TODO?: inject commit metadata, if missing
    #print(f"{annotated_bug_dataset.bugs=}")

    data_list = annotated_bug_dataset.gather_data_list(map_diff_to_timeline)

    # DEBUG
    #from pprint import pprint
    #pprint(data_list)

    # NOTE: change if the test data changes!
    assert len(data_list) == 1, \
        "only one annotation file was present"
    assert data_list[0]['bug_id'] == 'CVE-2021-21332', \
        "found expected bug id"

    # NOTE: change if the test data changes!
    annotation_file = 'e54746bdf7d5c831eabe4dcea76a7626f1de73df.json'
    assert data_list[0]['patch_id'] == annotation_file, \
        "found expected annotation file"

    diff_data = data_list[0]
    assert {'file_names', '+:count', '-:count'} <= set(diff_data.keys()), \
        "expected common keys present in extracted stats"
    # NOTE: change this single assert if the test data changes!
    assert {
        '-:type.code', '+:type.code', '-:type.documentation', '+:type.documentation'
    } <= set(diff_data.keys()), \
        "expected keys for line types present in extracted stats"
    assert ('-:type.test' not in diff_data and
            '+:type.test' not in diff_data), \
        "there are no lines with type 'test' at all, with defaults"
    assert ('-:type.other' not in diff_data and
            '+:type.other' not in diff_data), \
        "there are no lines with type 'other' at all, with defaults"

    data_list = annotated_bug_dataset.gather_data_list(map_diff_to_timeline,
                                                       purpose_to_annotation=[('test', 'test'),
                                                                              ('other', 'other')])
    diff_data = data_list[0]

    # DEBUG
    #from pprint import pprint
    #print(f"passing purpose_to_annotation")
    #pprint(data_list)

    # NOTE: change if the test data changes, e.g. different annotated diff!
    assert ('-:type.other' in diff_data or
            '+:type.other' in diff_data), \
        "there are lines that have type 'other' thanks to purpose_to_annotation"


def test_PurposeCounterResults_create():
    data = {
        "synapse/push/mailer.py": {
            "language": "Python",
            "type": "programming",
            "purpose": "programming",
            "+": [
                {
                    "id": 3,
                    "type": "code",
                    "purpose": "programming",
                    "tokens": [
                        [
                            51,
                            [
                                "Text",
                                "Whitespace"
                            ],
                            "    "
                        ],
                        [
                            55,
                            [
                                "Literal",
                                "String",
                                "Doc"
                            ],
                            "\"\"\"\n"
                        ]
                    ]
                }
            ]
        }
    }
    result = PurposeCounterResults.create('e54746bdf7d5c831eabe4dcea76a7626f1de73df.json', data)
    assert result._processed_files == ['e54746bdf7d5c831eabe4dcea76a7626f1de73df.json']
    assert result._hunk_purposes == Counter({'programming': 1})
    assert result._added_line_purposes == Counter({'programming': 1})
    assert result._removed_line_purposes == Counter()
