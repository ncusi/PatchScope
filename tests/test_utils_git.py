# -*- coding: utf-8 -*-
"""Test cases for 'src/diffannotator/utils/git.py' module"""
import subprocess
import textwrap
from typing import Optional

import psutil
import pytest
from unidiff import PatchSet, PatchedFile

from diffannotator.utils.git import decode_c_quoted_str, GitRepo, DiffSide, AuthorStat, parse_shortlog_count, ChangeSet, \
    maybe_close_subprocess, get_patched_file_mode, changes_survival_perc, GitFileMode
from tests.conftest import default_branch, example_repo, example_repo_utf8


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


def test_unidiff_missing(example_repo):
    """Test handling of missing commit by GitRepo.unidiff"""
    with pytest.raises(subprocess.CalledProcessError):
        example_repo.unidiff('non_existent')


def test_changed_lines_extents(example_repo):
    # TODO?: use pytest-subtest plugin
    # with self.subTest("for HEAD (last commit)"):
    actual, _, _ = example_repo.changed_lines_extents()
    expected = {
        'new_file': [(1,10)],  # whole file added in v2
        'renamed_file': [(4,4)],  # file renamed in v2 from 'example_file', changed line 4
        'subdir/subfile': [(2,2)],  # file modified in v2 without name change
    }
    assert expected == actual, "changed lines for post-image for changed files match (HEAD)"

    # with self.subTest("for v1 (first commit, root)"):
    actual, _, _ = example_repo.changed_lines_extents('v1')
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


def test_batch_command(example_repo):
    """Test that the GitRepo.batch_command property behaves sanely"""
    assert example_repo._cat_file is None, "the property is not initialized yet"

    maybe_close_subprocess(example_repo._cat_file)  # no error

    procs = psutil.Process().children(recursive=False)
    assert not [p for p in procs if p.name() in {'git', 'git.exe'}], \
        "there is no 'git' process running before .batch_command"

    proc_1 = example_repo.batch_command
    proc_2 = example_repo.batch_command
    assert proc_1 is proc_2, ".batch_command property is cached"

    procs = psutil.Process().children(recursive=False)
    assert len([p for p in procs if p.name() in {'git', 'git.exe'}]) == 1, \
        "there is a single 'git' process started after .batch_command"

    proc: Optional[subprocess.Popen] = example_repo._cat_file
    assert proc is not None, "process was generated by .batch_command, and is not None"
    assert isinstance(proc, subprocess.Popen), "process is a Popen object"
    assert proc.returncode is None, "the `git cat-file` didn't return (process is live)"

    actual = example_repo.are_valid_objects(["HEAD"])
    expected = [True]
    assert actual == expected, ".are_valid_object('HEAD') returns True"

    maybe_close_subprocess(example_repo._cat_file)  # no error

    proc = example_repo.batch_command
    assert isinstance(proc, subprocess.Popen), ".batch_command returns a Popen object"
    assert proc.returncode == 0, "the `git cat-file` returns success (process ended)"

    procs = psutil.Process().children(recursive=False)
    assert not [p for p in procs if p.name() in {'git', 'git.exe'}], \
        "there is no 'git' process running after calling maybe_close_subprocess()"

    with pytest.raises(ValueError) as exc_info:
        example_repo.are_valid_objects(["HEAD"])
    assert "closed file" in str(exc_info.value), "the `git cat-file` process is closed"

    example_repo.close_batch_command()  # no errors

    #print(f"{example_repo._finalizer=}")
    #print(f"{example_repo._finalizer.alive=}")
    #print(f"{example_repo._finalizer.peek()=}")
    #print(f"{example_repo._finalizer()=}")
    #print(f"{example_repo._finalizer.detach()=}")
    #print(f"{example_repo._finalizer.alive=}")


@pytest.mark.xfail(reason="known failure of ._finalize() in .close_batch_command()")
def test_close_batch_command(example_repo):
    """Test that GitRepo.close_batch_command() works correctly"""
    assert example_repo._cat_file is None, \
        "the ._cat_file property is not initialized by default"

    proc = example_repo.batch_command
    assert example_repo._cat_file is not None, \
        "the ._cat_file property is initialized by .batch_command"
    assert proc.returncode is None, \
        "the `git cat-file` didn't return (process is live)"
    assert proc == example_repo._cat_file, \
        "the ._cat_file property caches what .batch_command returns"

    # main part of this test
    example_repo.close_batch_command()
    assert example_repo._cat_file is None, \
        "the ._cat_file property is set to None by .close_batch_command()"

    procs = psutil.Process().children(recursive=False)
    assert not [p for p in procs if p.name() in {'git', 'git.exe'}], \
        "there is no 'git' process running after calling .close_batch_command()"


def test_are_valid_objects(example_repo):
    """Test that GitRepo.are_valid_objects returns the correct answer"""
    actual = example_repo.are_valid_objects(['HEAD', 'v1', 'v2'], object_type='commit')
    assert actual == [True, True, True], "all provided commits are valid"

    actual = example_repo.are_valid_objects(['non_existent', 'v3', 'HEAD~20'], object_type='commit')
    assert actual == [False, False, False], "all provided commits are invalid"

    # a shortened sha-1 identifier needs to be at least 4 characters long
    # you need a large enough repository to have an ambiguous 4-character prefix
    # this very repository (current repository) is large enough (using any object)
    #actual = GitRepo('.').are_valid_objects(['dedf', 'caa2'], object_type=None)
    #assert actual == [None, None], "all provided objects are ambiguous"


def test_filter_valid_commits(example_repo):
    """Test that GitRepo.filter_valid_commits returns the correct answer"""
    filtered = example_repo.filter_valid_commits(['HEAD', 'non_existent', 'v1', 'v2', 'v3', 'HEAD~20'])
    assert list(filtered) == ['HEAD', 'v1', 'v2'], "filter only valid commits"

    filtered = example_repo.filter_valid_commits(['HEAD', 'non_existent', 'v1', 'v2', 'v3', 'HEAD~20'], to_oid=True)
    assert len(list(filtered)) == 3, "there were 3 valid commits (now oids)"


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


def test_reverse_blame(example_repo, subtests):
    with subtests.test("reverse blame from v1.5"):
        commits_data, line_data = example_repo.reverse_blame('v1.5', 'subdir/subfile')
        # single line that survived
        assert len(line_data) == 1, "there was single line in v1.5"
        blame_commit = line_data[0]['commit']
        assert 'previous' not in commits_data[blame_commit],\
            "survived until commit with no previous (last commit)"
        assert blame_commit == example_repo.to_oid("HEAD"),\
            "reverse blame commit is HEAD (last commit)"

    with subtests.test("reverse blame from v1"):
        commits_data, line_data = example_repo.reverse_blame('v1', 'subdir/subfile')
        # single line that did not survive for even a single commit
        # and that commit was v1.5, which is not the last commit
        assert len(line_data) == 1, "there was single line in v1"
        blame_commit = line_data[0]['commit']
        assert 'previous' in commits_data[blame_commit],\
            "did not survive until commit with no previous (last commit)"
        assert 'boundary' in commits_data[blame_commit],\
            "was changed in subsequent commit"
        assert blame_commit == example_repo.to_oid("v1"),\
            "reverse blame commit is starting commit v1"

    with subtests.test("reverse blame with line range"):
        line_extent = (2, 3)
        n_lines = line_extent[1] - line_extent[0] + 1
        _, line_data = example_repo.reverse_blame(
            commit='v1', file='example_file',
            line_extents=[line_extent]
        )
        # requested two lines, got two lines
        assert len(line_data) == n_lines, f"reverse blame returned {n_lines} lines"
        # line numbers match
        for blame_line, line_no in zip(line_data, line_extent, strict=True):
            assert int(blame_line['final']) == line_no, f"line number match for line number {line_no}"


def test_changes_survival(example_repo, subtests):
    # for a more universal replacement of UnitTest.assertCountEqual in pytest,
    # see https://stackoverflow.com/questions/41605889/does-pytest-have-an-assertitemsequal-assertcountequal-equivalent
    with subtests.test("changes survival from v1.5"):
        _, survival_info = example_repo.changes_survival("v1.5")
        # single file changed, single line change, which survived
        # was: self.assertCountEqual(survival_info.keys(), ['subdir/subfile'])
        assert list(survival_info.keys()) == ['subdir/subfile'], "v1.5: single file changed"
        assert len(survival_info['subdir/subfile']) == 1, "v1.5: single line change"
        assert 'previous' not in survival_info['subdir/subfile'][0], "v1.5: changed line survived"

    with subtests.test("changes survival from v1"):
        _, survival_info = example_repo.changes_survival(
            commit="v1",
            prev=example_repo.empty_tree_sha1
        )
        # two files created in v1
        # was: self.assertCountEqual(...)
        assert sorted(survival_info.keys()) == sorted([
            'example_file',
            'subdir/subfile',
        ]), "v1: two files created"
        # changes in 'subdir/subfile' consist of a single line that did not survive
        assert len(survival_info['subdir/subfile']) == 1,\
            "v1: single line change in 'subdir/subfile'"
        assert 'previous' in survival_info['subdir/subfile'][0],\
            "v1: line change in 'subdir/subfile' did not survive"
        # 4 lines out of 5 survived from 'example_file', 1 line in 'subdir/subfile' did not
        assert changes_survival_perc(survival_info) == (5-1, 5+1),\
            "v1: survival percentages match expectations"

    with subtests.test("changes survival from v1 (addition_optimization=True)"):
        _, survival_info = example_repo.changes_survival(
            commit="v1",
            prev=example_repo.empty_tree_sha1,
            addition_optimization=True
        )
        # two files created in v1
        assert sorted(survival_info.keys()) == sorted([
            'example_file',
            'subdir/subfile',
        ]), "v1: two files changed (created)"

    with subtests.test("changes survival from v2"):
        _, survival_info = example_repo.changes_survival("v2")
        # everything in changes survived because v2 is the last commit
        assert sorted(survival_info.keys()) == sorted([
            'new_file',
            'renamed_file',
            'subdir/subfile',
        ]), "v2: three files changed"
        for path, lines in survival_info.items():
            for line_info in lines:
                assert 'previous' not in line_info,\
                    f"v2: {path!r} file survived"


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


def test_ChangeSet_from_filename():
    commit_id = 'c0dcf39b046d1b4ff6de14ac99ad9a1b10487512'
    filename_diff_only = f'tests/test_dataset/tqdm-1/{commit_id}.diff'
    changeset_diff_only = ChangeSet.from_filename(filename_diff_only)

    assert isinstance(changeset_diff_only, ChangeSet), \
        "ChangeSet.from_filename returned ChangeSet or derived class"
    assert isinstance(changeset_diff_only, PatchSet), \
        "ChangeSet.from_filename returned PatchSet or derived class"
    assert changeset_diff_only.commit_id == commit_id, \
        "Extracted commit_id from file name"
    assert changeset_diff_only.commit_metadata is None, \
        "For file with diff only there is no way to get commit metadata from it"

    filename_diff_full = f'tests/test_dataset/tqdm-1/{commit_id}.diff_with_raw'
    changeset_diff_full = ChangeSet.from_filename(filename_diff_full)
    assert changeset_diff_full.commit_id == commit_id, \
        "Extracted commit_id from metadata matches with from file name"
    assert changeset_diff_full.commit_metadata is not None, \
        "Successful extraction of commit metadata from raw with patch format"
    assert changeset_diff_full.commit_metadata['id'] == commit_id, \
        "Commit id from metadata matches expectations"
    # NOTE: this depends on the test file used!
    assert changeset_diff_full.commit_metadata['message'].count('\n') == 1, \
        "The commit message has exactly one line, ending in '\\n'"


def test_ChangeSet_from_patch_file_with_cr():
    diff_filename = 'tests/test_dataset/qtile/4424a39ba5d6374cc18b98297f6de8a82c37ab6a.diff'

    ChangeSet.from_filename(diff_filename)

    # there were no exceptions


def test_get_patched_file_mode(subtests):
    """Test the `get_patched_file_mode()` function for different cases"""
    with subtests.test("binary files, no mode change"):
        diff_no_mode_change = 'tests/test_dataset/binary_files_differ.diff'
        patch = ChangeSet.from_filename(diff_no_mode_change)
        changed_file = patch[0]
        actual_src = get_patched_file_mode(changed_file,
                                           side=DiffSide.PRE)
        actual_dst = get_patched_file_mode(changed_file,
                                           side=DiffSide.POST)
        expected = '100644'  # ordinary file
        assert actual_src == expected, "source file mode matches"
        assert actual_dst == expected, "destination file mode matches"

    with subtests.test("ordinary files, with mode change"):
        diff_with_mode_change = 'tests/test_dataset/with_mode_change.diff'
        patch = ChangeSet.from_filename(diff_with_mode_change)
        changed_file = patch[0]
        actual_src = get_patched_file_mode(changed_file,
                                           side=DiffSide.PRE)
        actual_dst = get_patched_file_mode(changed_file,
                                           side=DiffSide.POST)
        expected_src = '100644'
        expected_dst = '100755'
        assert actual_src == expected_src, "source file mode matches"
        assert actual_dst == expected_dst, "destination file mode matches"

    with subtests.test("submodule without --recurse-submodules"):
        diff_new_submodule = 'tests/test_dataset/with_submodule.diff'
        patch = ChangeSet.from_filename(diff_new_submodule)
        changed_file = patch[0]
        actual = get_patched_file_mode(changed_file)
        expected = '160000'
        assert actual == expected, "submodule file mode matches"


def test_submodule_avoidance_logic():
    """Test submodule avoidance logic in GitRepo.changes_survival()"""
    # from https://github.com/synth-inc/onit
    patch_file = 'tests/test_dataset/6570767134ab5ff4d7e1a2fd761b4fc6c731d5ce.patch'
    changeset = ChangeSet.from_filename(patch_file)

    assert hasattr(changeset, 'commit_id'), \
        "ChangeSet has commit_id extracted from patch file name"

    # map from the file name in changed files to unidiff.PatchedFile for that file
    patched_files_map = {}
    patched_file: PatchedFile
    for patched_file in changeset:
        # the same key as used in .changed_lines_extents()
        patched_files_map[decode_c_quoted_str(patched_file.path)] = patched_file

    assert 'LLMStream' in patched_files_map, \
        "'LLMStream' path is in files/paths changed by the patch"

    file_path = 'LLMStream'
    file_mode = get_patched_file_mode(patched_files_map[file_path], file_path)

    assert file_mode == GitFileMode.SUBMODULE, \
        "'LLMStream' file mode marks it as a submodule"

    assert file_mode == GitFileMode.SUBMODULE.value, \
        "'LLMStream' file mode marks it as a submodule"


def test_repo_utf8(example_repo_utf8):
    """"Test all GitRepo methods that deal with filenames, etc., on utf-8 data"""
    expected = ['przykładowy plik']
    actual = example_repo_utf8.list_files()
    assert sorted(expected) == sorted(actual), "list_files() matches"

    expected = ['przykładowy plik']
    actual = example_repo_utf8.list_changed_files()
    assert sorted(expected) == sorted(actual), "list_changed_files() matches"

    expected = {('przykładowy plik', 'przykładowy plik'): 'M'}
    actual = example_repo_utf8.diff_file_status()
    assert expected == actual, "diff_file_status() matches"

    expected = textwrap.dedent("""\
    diff --git "a/przyk\\305\\202adowy plik" "b/przyk\\305\\202adowy plik"
    index d66e895..000412a 100644
    --- "a/przyk\\305\\202adowy plik"\t
    +++ "b/przyk\\305\\202adowy plik"\t
    @@ -1,3 +1,5 @@
     zażółć
    -gęsią
    +gęślą
     jaźń
    +
    +Pójdź, kińże tę chmurność w głąb flaszy!
    \\ No newline at end of file
    """)
    actual = example_repo_utf8.unidiff(wrap=False)
    assert expected == actual, "unidiff(wrap=False) matches"

    actual = example_repo_utf8.unidiff(wrap=True)
    assert isinstance(actual, PatchSet), "unidiff(wrap=True) is wrapped in unidiff.PatchSet"
    # differs in tabs vs nothing at the end of ---/+++ lines
    # TODO: send a bug report for 'unidiff2'
    assert expected.replace('\t', '') == str(actual), "unidiff(wrap=True) matches stringification"

    # uses GitRepo.unidiff
    actual = example_repo_utf8.changed_lines_extents()
    expected = {'przykładowy plik': [(2, 2), (4, 5)]}
    assert expected == actual[0], "changed_lines_extents() matches extents"
    for file_name, extents_data in actual[0].items():
        n_lines = sum([pair[1] - pair[0] + 1 for pair in extents_data])
        assert n_lines == len(actual[1][file_name]),\
            f"changed_lines_extents() extents matches added lines for {file_name}"

    actual = example_repo_utf8.log_p(wrap=False)
    actual = list(actual)
    assert len(actual) == 1,\
        "log_p(wrap=False) by default returns single commit"
    assert "author A U Þór <author@example.com>" in actual[0],\
        "log_p(wrap=False) includes authorship information"

    actual = example_repo_utf8.log_p(wrap=True)
    actual = list(actual)
    assert len(actual) == 1, \
        "log_p(wrap=True) by default returns single commit"
    assert isinstance(actual[0], ChangeSet), "log_p(wrap=True) contains single ChangeSet."
    assert isinstance(actual[0], PatchSet), "log_p(wrap=True) contains single PatchSet."

    expected = "zażółć\ngęsią\njaźń\n"
    actual = example_repo_utf8.file_contents(commit="v1", path="przykładowy plik")
    assert expected == actual, "file_contents() at v1 matches"

    with example_repo_utf8.open_file(commit="v1", path="przykładowy plik") as fpb:
        actual = fpb.read().decode('utf8')
    assert expected == actual, "open_file() at v1 matches"

    actual = example_repo_utf8.get_commit_metadata()
    assert actual['author']['name'] == 'A U Þór',\
        "get_commit_metadata() author name matches"

    actual = example_repo_utf8.list_authors_shortlog()
    assert len(actual) == 1, "list_authors_shortlog() returned info about 1 author"
    count, author = actual[0].split('\t', maxsplit=1)
    assert int(count) == 2, "list_authors_shortlog() counted 2 commits"
    assert author == 'A U Þór', "list_authors_shortlog() returned correct author name"

    expected = "A U Þór"
    actual = example_repo_utf8.get_config("user.name")
    assert expected == actual, "get_config() returned correct 'user.name' value"
