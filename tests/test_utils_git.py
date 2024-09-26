# -*- coding: utf-8 -*-
"""Test cases for 'src/diffannotator/utils/git.py' module"""

import pytest
from unidiff import PatchSet

from diffannotator.utils.git import decode_c_quoted_str, GitRepo, DiffSide, AuthorStat, parse_shortlog_count, ChangeSet
from tests.conftest import default_branch, example_repo


def test_decode_c_quoted_str():
    """Test decode_c_quoted_str() function"""
    assert r'simple text' == decode_c_quoted_str(r'simple text'), \
        'non-encoded text passthrough'
    assert r'some text\with slash and "quote"' == \
           decode_c_quoted_str(r'"some text\\with slash and \"quote\""'), \
        'c-quoted quotation marks and backslashes'
    # NOTE: the test below does not use raw string for expected value,
    #       but uses ecape sentence to create string with literal TAB character
    #       as opposed to other test, which use raw string for easier reading
    assert 'some text with \t tab' == decode_c_quoted_str(r'"some text with \t tab"'), \
        'c-quoted tab character'
    assert r'zażółć' == decode_c_quoted_str(r'"za\305\274\303\263\305\202\304\207"'), \
        'c-quoted utf8'

    with pytest.raises(ValueError):
        decode_c_quoted_str(r'"unknown escape \x"')

    with pytest.raises(ValueError):
        decode_c_quoted_str(r'"interrupted octal escape \30z"')

    with pytest.raises(ValueError):
        decode_c_quoted_str(r'"unfinished escape \"')

    with pytest.raises(ValueError):
        decode_c_quoted_str(r'"unfinished octal escape \30"')

    with pytest.raises(ValueError):
        decode_c_quoted_str(r'"\305\477"')


def test_list_files(example_repo: GitRepo):
    """Test that GitRepo.list_files() returns correct list of files"""
    expected = [
        'example_file',
        'subdir/subfile'
    ]
    actual = example_repo.list_files('v1')
    assert sorted(expected) == sorted(actual), "list of files in v1"

    expected = [
        'renamed_file',
        'subdir/subfile',
        'new_file'
    ]
    actual = example_repo.list_files()
    assert sorted(expected) == sorted(actual), "list of files in HEAD"


def test_list_changed_files(example_repo: GitRepo):
    """Test that GitRepo.list_changed_files returns correct list of files"""
    expected = [
        'new_file',
        'subdir/subfile',
        'renamed_file',
    ]
    actual = example_repo.list_changed_files('v2')
    assert sorted(expected) == sorted(actual), "list of changed files in v2 (post)"

    expected = [
        # no 'new_file'
        'subdir/subfile',
        'example_file',  # before rename
    ]
    actual = example_repo.list_changed_files('v2', side=DiffSide.PRE)
    assert sorted(expected) == sorted(actual), "list of changed files in v2 (post)"


def test_diff_file_status(example_repo):
    """Test the result of GitRepo.diff_file_status"""
    expected = {
        (None, 'new_file'): 'A',  # file added in v2
        ('example_file', 'renamed_file'): 'R',  # file renamed in v2
        ('subdir/subfile',) * 2: 'M',  # file modified in v2 without name change
    }
    actual = example_repo.diff_file_status('v2')
    assert expected == actual, "status of changed files in v2"


def test_unidiff(example_repo):
    """Test extracting data from GitRepo.unidiff"""
    patch = example_repo.unidiff()
    files = [f.path for f in patch]
    expected = [
        'new_file',  # file added in v2
        'renamed_file',  # file renamed in v2 from 'example_file'
        'subdir/subfile',  # file modified in v2 without name change
    ]
    assert sorted(files) == sorted(expected), "extracted changed files match"
    diffstat = {
        f.path: (f.removed, f.added)
        for f in patch
    }
    assert diffstat['new_file'][0] == 0, "new file has no deletions"
    assert diffstat['renamed_file'] == (1,  1), "rename with changes"
    # before: 'subfile', after: 'subfile\nsubfile\n'
    assert diffstat['subdir/subfile'] == (0,  1), "changed file stats matches"

    expected_src = {
        # changed from 'subfile\n'
        #1: 'subfile'
    }
    expected_dst = {
        # changes to 'subfile\nsubfile\n'
        #1: 'subfile',
        2: 'subfile'
    }
    assert {
        line.source_line_no: line.value.strip()
        # there is only one hunk in changes in 'subdir/subfiles' file
        for line in patch[-1][0] if line.is_removed
    } == expected_src, "pre-image on last file matches"

    assert {
        line.target_line_no: line.value.strip()
        # there is only one hunk in changes in 'subdir/subfiles' file
        for line in patch[-1][0] if line.is_added
    } == expected_dst, "post-image on last file matches"


def test_unidiff_wrap(example_repo):
    """Test handling of `wrap` parameter in GitRepo.unidiff"""
    assert isinstance(example_repo.unidiff(), PatchSet), \
        "return PatchSet by default"
    assert isinstance(example_repo.unidiff(wrap=True), PatchSet), \
        "with wrap=True return unidiff.PatchSet"
    assert isinstance(example_repo.unidiff(wrap=True), ChangeSet), \
        "with wrap=True return utils.git.ChangeSet"
    assert isinstance(example_repo.unidiff(wrap=False), str), \
        "with wrap=False return str"


def test_changed_lines_extents(example_repo):
    # TODO?: use pytest-subtest plugin
    # with self.subTest("for HEAD (last commit)"):
    actual, _ = example_repo.changed_lines_extents()
    expected = {
        'new_file': [(1,10)],  # whole file added in v2
        'renamed_file': [(4,4)],  # file renamed in v2 from 'example_file', changed line 4
        'subdir/subfile': [(2,2)],  # file modified in v2 without name change
    }
    assert expected == actual, "changed lines for post-image for changed files match (HEAD)"

    # with self.subTest("for v1 (first commit, root)"):
    actual, _ = example_repo.changed_lines_extents('v1')
    expected = {
        'example_file': [(1,5)],  # whole file added in v1 with 5 lines
        'subdir/subfile': [(1,1)],  # whole file added in v2 with 1 incomplete line
    }
    assert expected == actual, "changed lines for post-image for changed files match (v1)"


def test_file_contents(example_repo):
    """Test that GitRepo.file_contents returns file contents as text"""
    expected = 'example\n2\n3\n4\n5\n'
    actual = example_repo.file_contents('v1', 'example_file')
    assert expected == actual, "contents of 'example_file' at v1"

    expected = 'example\n2\n3\n4b\n5\n'
    actual = example_repo.file_contents('v2', 'renamed_file')
    assert expected == actual, "contents of 'renamed_file' at v2"


def test_list_tags(example_repo):
        """Test that GitRepo.list_tags list all tags"""
        expected = ['v1', 'v1.5', 'v2']
        actual = example_repo.list_tags()

        assert expected == actual, "list of tags matches"


def test_get_commit_metadata(example_repo):
    commit_info = example_repo.get_commit_metadata('v2')

    assert commit_info['tree'] == '417e98fd5c1f9ddfbdee64c98256998958d901ce', \
        "'tree' field did not change"
    assert commit_info['message'] == 'Change some files\n\n* one renamed file\n* one new file\n', \
        "commit message matches"
    assert commit_info['author'] == {
        'author': 'Joe Random <joe@random.com>',
        'email': 'joe@random.com',
        'name': 'Joe Random',
        'timestamp': 1693605193,
        'tz_info': '-0600'
    }, "author info matches"
    assert commit_info['committer']['committer'] == 'A U Thor <author@example.com>', \
        "committer matches repository setup"


def test_is_valid_commit(example_repo):
    """Test that GitRepo.is_valid_commit returns correct answer

    Tested only with references and <rev>^ notation, as the test repository
    is not created in such way that SHA-1 identifiers are be stable; and
    currently GitRepo class lack method that would turn <commit-ish> or
    <object> into SHA-1 identifier.
    """
    # all are valid references that resolve to commit
    assert example_repo.is_valid_commit("HEAD"), "HEAD is valid"
    assert example_repo.is_valid_commit("v1"), "tag v1 is valid"
    assert example_repo.is_valid_commit("v2"), "tag v2 is valid"

    # all are not existing references
    assert not example_repo.is_valid_commit("non_existent"), "no 'non_existent' reference"

    # <rev>^ notation within existing commit history
    assert example_repo.is_valid_commit("HEAD^"), "HEAD^ is valid"

    # <rev>^ notation leading outside existing commit history
    assert not example_repo.is_valid_commit("HEAD^3"), "HEAD^3 is invalid"
    assert not example_repo.is_valid_commit("HEAD~20"), "HEAD~20 is invalid"


def test_get_current_branch(example_repo):
    """Basic test of GitRepo.get_current_branch"""
    assert example_repo.get_current_branch() == default_branch, \
        f"current branch is default branch: '{default_branch}'"


def test_resolve_symbolic_ref(example_repo):
    """Test that GitRepo.resolve_symbolic_ref works correctly"""
    assert \
        example_repo.resolve_symbolic_ref("HEAD") == \
        f'refs/heads/{default_branch}', \
        f"'HEAD' resolves to 'refs/heads/{default_branch}'"
    assert example_repo.resolve_symbolic_ref("v2") is None, \
        "'v2' is not a symbolic ref"


def test_check_merged_into(example_repo):
    """Test GitRepo.check_merged_into for various combinations of commit and into"""
    actual = example_repo.check_merged_into('v1')
    assert len(actual) > 0, "'v1' is merged [into HEAD]"
    actual = example_repo.check_merged_into('v1', ['refs/heads/', 'refs/tags/'])
    expected = [
        f'refs/heads/{default_branch}',
        'refs/tags/v1',
        'refs/tags/v1.5',
        'refs/tags/v2',
    ]
    assert sorted(expected) == sorted(actual), "'v1' is merged into HEAD, v1, v1.5, v2"
    actual = example_repo.check_merged_into('v2', 'refs/tags/v1')
    assert not actual, "'v2' is not merged into v1"


def test_count_commits(example_repo):
    """Basic tests for GitRepo.count_commits() method"""
    expected = 3  # v1, v1.5, v2

    # with self.subTest("default value of start_from"):
    actual = example_repo.count_commits()
    assert expected == actual, "number of commits in repository matches (default param)"

    # with self.subTest("for start_from='HEAD'"):
    actual = example_repo.count_commits('HEAD')
    assert expected == actual, "number of commits in repository matches (start_from='HEAD')"


def test_list_authors(example_repo):
    """Test GitRepo.list_authors_shortlog() and related methods"""
    expected = [
        '2\tA U Thor',  # author of v1, v1.5
        '1\tJoe Random',  # author of v2
    ]
    authors_shortlog = example_repo.list_authors_shortlog()
    actual_simplified = [
        info.strip()
        for info in authors_shortlog
    ]
    assert sorted(actual_simplified) == sorted(expected), "list of authors matches"

    expected = [
        AuthorStat(author='A U Thor', count=2),
        AuthorStat(author='Joe Random', count=1)
    ]
    actual = parse_shortlog_count(authors_shortlog)
    assert sorted(expected) == sorted(actual), "parsed authors counts matches"


def test_find_roots(example_repo):
    """Test GitRepo.find_roots() method"""
    roots_list = example_repo.find_roots()
    assert len(roots_list) == 1, "has a single root commit"

    v1_oid = example_repo.to_oid("v1")
    assert roots_list[0] == v1_oid, "root commit is v1"


def test_get_config(example_repo):
    """Test GitRepo.get_config() method"""
    expected = 'A U Thor'  # set up in setUpClass() class method
    actual = example_repo.get_config('user.name')
    assert expected == actual, "got expected value for 'user.name'"

    actual = example_repo.get_config('not-exists')
    assert actual is None, "returns `None` for invalid variable name"


def test_metadata_extraction_in_ChangeSet(example_repo):
    """Test that ChangeSet constructor can extract commit metadata"""
    revision = "v2"
    revision_id = example_repo.to_oid(revision)

    patch_bare = example_repo.unidiff(revision)

    assert patch_bare.prev == f"{revision}^", \
        ".unidiff() sets .prev field to expected value"
    assert patch_bare.commit_metadata is None, \
        ".unidiff() does not provide commit info to extract metadata"

    # single commit changeset, i.e. the first element from a single element generator
    patch_log = next(example_repo.log_p(revision_range=('-1', revision), wrap=True))
    revision_metadata = example_repo.get_commit_metadata(revision)

    assert patch_log.prev is None, \
        ".log_p() does not set .prev field"
    assert patch_log.commit_id == revision_id, \
        ".log_p() returns expected commit, and sets .commit_id to its oid"
    assert patch_log.commit_metadata is not None, \
        "extracted commit metadata from .log_p() result"
    assert patch_log.commit_metadata == revision_metadata, \
        "correctly extracted expected metadata from .log_p() result"
