# Annotation process

Installing the `patchscope` package installs scripts (currently three)
that you can run to generate patches, annotate them, and extract their statistics.
Every script name starts with the `diff-*` prefix.

Each script and subcommand (for those scripts that have multiple subcommands)
support the `--help` option.

- `diff-generate`: used to generate patches (`*.patch` and `*.diff` files)
  from a given repository, in the format suitable for later analysis;
  not strictly necessary;
- `diff-annotate`: annotates existing dataset (patch files in subdirectories),
  or annotates selected subset of commits (of changes in commits)
  in the given Git repository, producing annotation data (`*.json` files);
- `diff-gather-stats`: compute various statistics and metrics
  from patch annotation data generated by the `diff-annotate` script,
  usually producing a single `*.json` file.

## Usages

- <u>Usage:</u> `diff-generate [OPTIONS] REPO_PATH [REVISION_RANGE...]`<br>
  (where `REVISION_RANGE...` is passed as arguments to the `git log` command)

- <u>Usage:</u> `diff-annotate [OPTIONS] COMMAND [ARGS]...`
    - `diff-annotate patch [OPTIONS] PATCH_FILE RESULT_JSON`:
      annotate a single PATCH_FILE, writing results to RESULT_JSON,
    - `diff-annotate dataset [OPTIONS] DATASETS...`:
      annotate all bugs in provided DATASETS,
    - `diff-anotate from-repo [OPTIONS] REPO_PATH [REVISION_RANGE...]`:
      create annotation data for commits from local Git repository
      (with `REVISION_RANGE...` passed as arguments to the `git log` command);

- <u>Usage:</u> `diff-gather-stats [OPTIONS] COMMAND [ARGS]...`
    - `diff-gather-stats purpose-counter [--output JSON_FILE] DATASETS...`:
      calculate count of purposes from all bugs in provided datasets,
    - `diff-gather-stats purpose-per-file [OPTIONS] RESULT_JSON DATASETS...`:
      calculate per-file count of purposes from all bugs in provided datasets,
    - `diff-gather-stats lines-stats [OPTIONS] OUTPUT_FILE DATASETS...`:
      calculate per-bug and per-file count of line types in provided datasets,
    - `diff-gather-stats timeline [OPTIONS] OUTPUT_FILE DATASETS...`:
      calculate timeline of bugs with per-bug count of different types of lines;

## Patches source

There are two possible sources of patches (unified diffs) to annotate:
existing patch on disk, or git repository.

### Patches and patch datasets

The first possible data source is a **patch**, or series of patches (a **dataset**),
saved as a `*.diff` file on disk.  This can be some pre-existing dataset, like
BugsInPy[^BugsInPy-paper] - one with patches stored as files on disk
(instead of being stored in some database).  It can also be a result of running
the `diff-generate` script.

[^BugsInPy-paper]: R. Widyasari et.al.: _"BugsInPy: a database of existing bugs in Python programs to enable controlled testing and debugging studies"_, ESEC/FSE 2020,  pp. 1556–1560, https://doi.org/10.1145/3368089.3417943

Two of the `diff-annotate` subcommand support this type of the diff data source:

- `diff-annotate patch [OPTIONS] PATCH_FILE RESULT_JSON`:
  annotate a single PATCH_FILE, writing results to RESULT_JSON,
- `diff-annotate dataset [OPTIONS] DATASETS...`:
  annotate all bugs in provided DATASETS,

The **`patch`** subcommand of the `diff-annotate` command (script) is mainly
intended as a helper in examining and debugging the annotation process
and the annotation format.

The **`dataset`** subcommand is, instead, meant to annotate existing dataset
of patches, that is set of patches in specific directory or directories.

You can annotate more than one dataset (directory) at once, though they
need to have the same internal structure.  By default, each dataset is
expected to be an existing directory with the following path structure:

> &lt;dataset_directory&gt;/&lt;bug_directory&gt;/patches/&lt;patch_file&gt;.diff

This directory structure follows the structure used by the
BugsInPy[^BugsInPy-paper] dataset.  You can change the `/patches/`
part with the `--patches-dir` option, or eliminate it all together.
For example, with `--patches-dir=''`, the `diff-annotate` script
would expect data to have the following structure:

> &lt;dataset_directory&gt;/&lt;bug_directory&gt;/&lt;patch_file&gt;.diff

Each dataset can consist with one or more bugs, each bug should include
at least one `*.diff` file to annotate.

By default, annotation data is saved beside patches, in the same
directory structures, as JSON files - one file per patch / diff:

> &lt;dataset_directory&gt;/&lt;bug_directory&gt;/annotation/&lt;patch_file&gt;.json

You can change the `/annotation/` part with the `--annotations-dir` option.
You can also make `diff-annotate` save annotation data in a separate
place provided with the `--output-prefix` option (but with the same
directory structure as mentioned above).


### Git repository

Another source of patches to annotate are selected commits from
the local **git repository**.

One of `diff-annotate` subcommand support this type of the diff data source:

- `diff-anotate from-repo [OPTIONS] REPO_PATH [REVISION_RANGE...]`:
  create annotation data for commits from local Git repository
  (with `REVISION_RANGE...` passed as arguments to the `git log` command)

There is one required option: `--output-dir`, which you need to provide
for `diff-annotate from-repo` to know where to store the annotation data.
By default, the output JSON files are stored as:

> &lt;output_dir&gt;/&lt;commit_id&gt;.json
 
You can, if you want, create layout like the one in BugsInPy[^BugsInPy-paper]
(for example, when reproducing whole diffs instead of using simplified diffs
provided as `*.diff` files by the BugsInPy dataset).  If you expect many commits,
you can use `--use-fanout` flag to limit the number of files stored in
a single directory.

You can select which commits you want to annotate by providing appropriate
_&lt;revision-range&gt;_ argument, which is passed to `git log`.  If not provided,
it defaults to `HEAD` (that is, the whole history of the current branch).
For a complete list of ways to spell _&lt;revision-range&gt;_, see the
_"Specifying Ranges"_ section of the [gitrevisions(7) manpage](https://git-scm.com/docs/gitrevisions).

Here are a few `git log` options that are often used with
`diff-annotate from-repo`:

- `--max-parents=1`, or `--no-merges` is probably the most commonly used
  option; it limits commits to those with maximum of 1 parent, dropping
  merge commits (which as of PatchScope **0.4.1** are using the
  `--diff-merges=first-parent` to generate unified diff out of merge,
  comparing it against first parent, and often generating very large
  diff encompassing all changes made on merged in branch),
- `--min-parents=1` can be used to drop root commits (rarely used),
- `--author=<email>` or `--author=<name>` can be used to limit to
  commits authored (created) by a given author,
- `<tag1>..<tag2>` revision range specifier (like e.g. `v6.8..v6.9`)
  to select all changes between two tagged revisions, perhaps together
  with `--ancestry-path` option,
- date range with `--after=<date>` and/or `--before=<date>` (like
  e.g. `--after=2021.01.01 --before=2023.12.31`) to select all changes
  available from default / current / selected branch that were
  (note: stopping at the first commit which is older than a specific date,
  unless you use `--since-as-filter=<date>` instead of `--since` or `--after`).

To reproduce (redo) an existing bug dataset, provided that we know ids
of bug-fixing commits, can be currently (as of **0.4.1**) done with
the following `git log` option:

- `--no-walk <commit1> <commit2>...` to only process selected commits,
  but do not traverse their ancestors.

## File language detection

Next step in the annotation process is detecting the language and purpose
of each changed file in a diff.  This is done with the help of the
[GitHub Linguist][linguist], which is the library is used on GitHub\.com
to detect blob languages, ignore binary or vendored files, suppress generated
files in diffs, and generate language breakdown graphs.

To be more exact, language detection and file purpose detection is done
by a custom code that uses [`language.yml`](https://github.com/github-linguist/linguist/blob/main/lib/linguist/languages.yml)
file from GitHub Linguist (or rather its local copy), and some custom rules.

[linguist]: https://github.com/github-linguist/linguist "GitHub Linguist: Language Savant"

This code is more limited than GitHub Linguist, as it (currently, as of **0.4.1**)
uses only the pathname of the file (extension, basename, directory it is in),
and it does not examine its contents (which, in the case of patches and datasets
might be not available; in the case of repositories, it would have to be retrieved
from specific commit in the repository).

On the other hand, PatchScope's custom rules provide more types of file purpose
than GitHub Linguists' data, programming, markup, prose, or nil.  Those new
purposes include project, documentation, test, or unknown.

File purpose of changed file can and is later used to annotate changed line
in that file with type of the changed line.

The result of file language detection is the following mapping (dict):
```python
{
    "language": language,    # e.g. "Markdown"
    "type": filetype,        # e.g. "prose"
    "purpose": file_purpose  # e.g. "documentation"
}
```

### Using PyLinguist _(optional)_

[GitHub Linguist][linguist] is a Ruby library, which makes it difficult to
integrate with Python-based PatchScope.  There is, however, a Python clone
of [github/linguist][linguist].  The version available from PyPI is not the most
up to date; you can install the [retanoj/linguist](https://github.com/retanoj/linguist) fork
of original [douban/linguist](https://github.com/douban/linguist) Python clone
(itself fork of [liluo/linguist](https://github.com/liluo/linguist/))
with
```commandline
pip install patchscope[pylinguist]
```
or directly with
```commandline
pip install linguist@git+https://github.com/retanoj/linguist#egg=master
```

As of PatchScope version **0.4.1**, using PyLinguist, which you can turn on
with `--use-pytlinguist` global option of the `diff-annotate` script, still
only uses pathname of changed file.

Note that PyLinguist does not keep its `languages.yml` up to date, that is
why by default `diff-annotate` will make it use its own copy of the file.
You can turn it off with `--no-update-languages` flag.

All language detection code is in `diffannotator.languages` module
(which is created from the `src/diffannotator/languages.py` file).

### Build-in custom rules

The custom rules for language and purpose detection of changed files
is contained in 3 global variables and 2 functions.

Both `FILENAME_TO_LANGUAGES` and `EXT_TO_LANGUAGES` are used to augment
and override what GitHub Linguist' `languages.yml` detects as **language**
of the changed file, or provide language when `languages.yml` does not
detect it.

For example, `languages.yml` detects `README.me`, `read.me`, `readme.1st`
as "Text" files with purpose (called 'type' by GitHub Linguist) of "prose",
but not the plain `README` file.  The `FILENAME_TO_LANGUAGES` variable
handles this case.

On the other hand, the ".md" extension is assigned by `languages.yml`
to both "Markdown" (type: prose), and "GCC Machine Description" (type: programming).
The `EXT_TO_LANGUAGES` variable contents is used to break this tie
in favor of "Markdown".

There is yet another source of custom rules for finding file language,
namely the `languages_exceptions()` function that takes file path of the
changed file in the repository, and file language determined so far, and
determines file language (same as determined so for, or changed).

Beside language name, `languages.yml` also provides the `type` field,
which `diff-annotate` script presents as file **purpose**.  Here,
the `PATTERN_TO_PURPOSE` variable can be used to augment or override
the data from `languages.yml`.

For example, it defines patterns for "project" files (like `*.cmake`
or `requirements.txt`), something that is missing from the list of possible
file types in `languages.yml`.

> Note that as of PatchScope version **0.4.1**, pattern matching
> (which uses shell wildcards) is done using [`PurePath.match`][PurePath.match]
> method from the Python [pathlib][] standard library, with its limitations.
> Currently the recursive wildcard “`**`” acts like non-recursive “`*`”.
> This may change in the future.
 
[PurePath.match]: https://docs.python.org/3/library/pathlib.html#pathlib.PurePath.match
[pathlib]: https://docs.python.org/3/library/pathlib.html "The Python Standard Library » File and Directory Access » pathlib — Object-oriented filesystem paths"

There is yet another source of custom rules for finding file purpose,
namely the `_path2purpose()` static method in `Languages` class
in `diffannotator.languages` module.  It is this method that finds
"test" files, and which translates GitHub Linguist's "prose" file type
to PatchScope's "documentation" file purpose.

### Configuration from command line

Both finding file language and finding file purpose is configurable
from the command line.

- `--ext-to-language` defines mapping from extension to file language.<br>
  Examples of use include `--ext-to-language=.rs:Rust` and
  `--ext-to-language=".S:Unix Assembly"`, or `--ext-to-language=.cgi:Perl`
  (the last one is a project-specific rule).
- `--filename-to-language` defines mapping from filename to file language.<br>
  Examples of use include  `--filename-to-language=changelog:Text`,
  `--filename-to-language=config.mak.in:Makefile`, etc.
- `--pattern-to-purpose` defines mapping from filename pattern
  to that file purpose.<br>
  Examples of use include `--pattern-to-purpose=Makefile.*:project`,
  `--pattern-to-purpose=*.dts:data`, and `--pattern-to-purpose=*.dts?:data`.

In all those options, empty value resets mapping.

## Tokenizing changes

Next step involves using a lexer or a parser for changes or for a whole
changed file.  Currently (as of version **0.4.1**) the only supported
lexer is the [Pygments][] syntax highlighting library in Python.

The code that runs the lexer can be found in `diffannotator.lexer` module,
which is created from the `src/diffannotator/lexer.py` source code file.
This code is responsible for selecting and caching lexers, handling errors,
etc.

The lexing process uses the [`.get_tokens_unprocessed(text)`](https://pygments.org/docs/api/#pygments.lexer.Lexer.get_tokens_unprocessed)
method from `Lexer` class because it provides, as one of values, the starting
position of the token within the input text (index); it returns an iterable of 
`(&lt;index&gt;, &lt;tokentype&gt;, &lt;value&gt;)` tuples.  This is required to be able to
split multiline tokens in such way that we have correct tokenization
of each changed line.  Per-line tokenization is in turn needed to determine
the type (kind) of the line.

### Lexer selection

The Pygments lexer is selected using the
[`.get_lexer_for_filename(_fn, code=None, **options)`](https://pygments.org/docs/api/#pygments.lexers.get_lexer_for_filename)
method (passing only the filename, as of version **0.4.1**).

If no lexer is found, then `diff-annotate` uses Text lexer
([`TextLexer`](https://pygments.org/docs/lexers/#pygments.lexers.special.TextLexer))
as a fallback (as of version **0.4.1**).

Lexers are cached under file extension (suffix).

### Input for lexer

If the source of patches (unified diffs) are patches on disk, then what
is passed to the lexer is pre-image hunk or post-image hunk reconstructed,
respectively, from context lines and deleted lines or context lines and
added lines.

For example, given the following patch
```diff
diff --git a/tqdm/contrib/__init__.py b/tqdm/contrib/__init__.py
index 1dddacf..935ab63 100644
--- a/tqdm/contrib/__init__.py
+++ b/tqdm/contrib/__init__.py
@@ -38,7 +38,7 @@ def tenumerate(iterable, start=0, total=None, tqdm_class=tqdm_auto,
         if isinstance(iterable, np.ndarray):
             return tqdm_class(np.ndenumerate(iterable),
                               total=total or len(iterable), **tqdm_kwargs)
-    return enumerate(tqdm_class(iterable, start, **tqdm_kwargs))
+    return enumerate(tqdm_class(iterable, **tqdm_kwargs), start)


 def _tzip(iter1, *iter2plus, **tqdm_kwargs):
```
the pre-image hunk would be
```python
        if isinstance(iterable, np.ndarray):
            return tqdm_class(np.ndenumerate(iterable),
                              total=total or len(iterable), **tqdm_kwargs)
    return enumerate(tqdm_class(iterable, start, **tqdm_kwargs))


def _tzip(iter1, *iter2plus, **tqdm_kwargs):
```
That is what would get passed to lexer to allow for extracting tokenization
of deleted lines, in this case it would be the following line:
```python
    return enumerate(tqdm_class(iterable, start, **tqdm_kwargs))
```
The same process is applied to post-image of the hunk and to added lines.

If this change (this diff) was extracted from the tqdm project repository,
instead of passing pre-image or post-image hunk of changes to the lexer,
we can pass whole pre-image or post-image file contents.

In this case, the change came from the commit [`c0dcf39`](https://github.com/tqdm/tqdm/commit/c0dcf39b046d1b4ff6de14ac99ad9a1b10487512)
in the [tqdm](https://github.com/tqdm/tqdm) repository.  The pre-image
file contents would be [`8cc777fe:tqdm/contrib/__init__.py`](https://github.com/tqdm/tqdm/blob/8cc777fe8401a05d07f2c97e65d15e4460feab88/tqdm/contrib/__init__.py),
and post-image contents would be [`c0dcf39:tqdm/contrib/__init__.py`](https://github.com/tqdm/tqdm/blob/c0dcf39b046d1b4ff6de14ac99ad9a1b10487512/tqdm/contrib/__init__.py).

The `diff-annotate patch ...` and `diff-annotate dataset ...` pass pre-image
and post-image hunk to lexer, while `diff-annotate from-repo ...` passes
whole pre-image ad post-image file contents.  In the latter case, you can
turn off this feature (e.g. to achieve better performance) with `--no-use-repo`
option.

[Pygments]: https://pygments.org/ "Pygments: Python syntax highlighter"


## Determining line type (kind)

The next step is processing changed lines, one by one, and (among others)
determining the line type (line kind).

### Build-in rules

The custom rules for language and purpose detection of changed files
is contained 1 variable and in 3 function.

The `PURPOSE_TO_ANNOTATION` global variable is (as of version **0.4.1**)
used to determine the type (kind) of the line in a very simple way:
if the changed file pathname (before changes, or after changes, respectively)
matches one of pattern contained in `PURPOSE_TO_ANNOTATION`, then the
whole line has this purpose as line type.  In this case we don't perform
or retrieve tokenization (lexing).

Otherwise, the following rule is applied (see code in `.process()` method
of the `AnnotatedHunk` class in `diffannotator.annotate` module):

1. If line passes `line_is_comment()` test, then its type is "documentation".
2. Otherwise, `purpose_to_default_annotation()` function is consulted,
   which returns "code" for files with purpose of "programming",
   or file purpose as line type otherwise.

Line is declared as comment (by `line_is_comment()`) if the following
conditions are all true:

- among line tokens there is at least one token corresponding to comments
- there are only comment tokens or whitespace tokens in that line


### Configuration from command line

You can change how changed line are processed by providing line callback
with the `--line-callback` option.

The `--line-callback` option is modeled on the [callbacks in git-filter-repo](https://htmlpreview.github.io/?https://github.com/newren/git-filter-repo/blob/docs/html/git-filter-repo.html#CALLBACKS).
You can use it in one of two ways.

First possibility is to provide the body of the callback function
on the command line, using the command line argument like
```commandline
diff-annotate --line-callback 'BODY' ...
```
For this case, the following code will be compiled and called:
```python
def line_callback(file_data, tokens):
    BODY
```
Thus, you just need to make sure your _BODY_ returns appropriate line type
(as string value).  Note that the `diff-annotate` script checks for
the existence of this `return` statement.

Second possibility is to provide the path name to a file with
the callback function
```commandline
diff-annotate --line-callback <callback_script.py>
```
An example of such callback function can be found in `data/experiments/`,
in the `HaPy-Bug/` subdirectory, as [`hapybug_line_callback_func.py`](../data/experiments/HaPy-Bug/hapybug_line_callback_func.py):

```python

{%
    include "../data/experiments/HaPy-Bug/hapybug_line_callback_func.py"
    recursive=false
%}

```

> Note: actually, the `diff-annotate` script processing the `--line-callback`
> parameter first checks if it can be interpreted as file name, and if file
> with given pathname does not exist, it interprets this parameter as function
> or function body.
>
> For the parameter contents or the file contents to be interpreted as
> function definition rather than as function body, the content must start
> with `def ` on its first line.
>
> (as of PatchScope version **0.4.1**)


## Computing commit and diff metadata

Beside annotating each changed line, and each changed file, the `diff-annotate`
script also gathers metadata and computes statistics about the commit the
changes (changeset) belong to, and about diff (changes) as a whole.

### Commit metadata

Currently (as of version **0.4.1**), commit metadata is available only for
`from-repo` command, or maybe if `git show` or `git log -p` was saved as
the `*.diff` file to be parsed.  There is no support yet for `*.patch`
files with `git format-patch` output, or for parsing `*.message` files
accompanying bare-diff `*.diff` files (like in the BugsInPy dataset[^BugsInPy-paper]).

The following commit metadata is extracted and stored:

- commit ID
- parents (commit IDs of commit parents)
- tree ID
- author and committer
  - name
  - email
  - timestamp
  - timezone
- commit message

### Diff metadata

The diff metadata is computed by default, unless `--no-sizes-and-spreads`
flag is passed to the `diff-annotate` script.

The following basic diff metadata is stored:
- number of changed files (file names involved);
- number of added, removed, and renamed files, and of changed binary files (if any),
- number of added and removed lines,
  i.e. total number of '+' and '-' lines in hunks of patched file
- total number of hunks (in the unified diff meaning)

#### Patch size metrics

The definition of patch size (and its components) was taken from
the Defects4J-Dissection paper[^defects4j-dissection].

[^defects4j-dissection]: Victor Sobreira, Thomas Durieux, Fernanda Madeiral, Martin Monperrus, and Marcelo de Almeida Maia _"Dissection of a Bug Dataset: Anatomy of 395 Patches from Defects4J"_, SANER 2018, https://doi.org/10.1109/SANER.2018.8330203

The patch size metric is sum of the number of added, modified, and removed (deleted) lines.
Lines are considered _modified_ when sequences of removed lines are straight followed by added lines ~~(or vice versa).~~
To count each modified line, a pair of adjacent added and removed lines is needed.

Note that it is not always that first deleted line corresponds to first added line,
creating modified line.  Current algorithm only computes the numbers, but does
not tell which changed lines counts as modified, and which as removed or added.

The current algorithm does not always give the correct results.  It cannot
distinguish total rewrite from a modification, see for example
the [928a0447 commit](https://github.com/qtile/qtile/commit/928a0447f52a24f0c39cc135cb958a551c3855bb)
from the qtile repository:

```diff
diff --git a/docs/manual/releasing.rst b/docs/manual/releasing.rst
index ff7b31eb..0b935ee0 100644
--- a/docs/manual/releasing.rst
+++ b/docs/manual/releasing.rst
@@ -39,9 +39,10 @@ Be sure that you GPG-sign (i.e. the ``-S`` argument to ``git commit``) this comm
 6. Make sure all of these actions complete as green. The release should show up
    in a few minutes after completion here: https://pypi.org/project/qtile/

-7. send a mail to qtile-dev@googlegroups.com; I sometimes just use
-   git-send-email with the release commit, but a manual copy/paste of the
-   release notes into an e-mail is fine as well. Additionally, drop a message
-   in IRC/Discord.
+7. Push your tag commit to master.
+
+8. Update `the release string
+   <https://github.com/qtile/qtile.org/blob/master/config.toml#L49>`_ on
+   qtile.org.

 8. Relax and enjoy a $beverage. Thanks for releasing!

```
The current version of the algorithm (as of PatchScope **0.4.1**),
says  that there are 4 modified lines and 1 added line,
while in reality  this part was completely rewritten,
and the correct answer should be 4 deletions (removals) and 5 additions.

Here are all metrics that relate to the diff size
(counting number and size of changes):

- total number of hunks (in the unified diff meaning)
- total number of modified, added and removed lines for patched file, counting
  a pair of adjacent removed and added line as single modified line,
- total number of changed lines: sum of number of modified, added, and removed lines,
  (where numbers of modified, added and removed lines are defined as described above),
- total number of '+' and '-' lines in hunks of patched file (without extracting modified lines),
- number of all lines in all hunks of patched file, including context lines,
  but excluding hunk headers and patched file headers.

#### Patch spread metrics

The definition of patch spread metrics was also taken from
the Defects4J-Dissection paper[^defects4j-dissection].  These
metrics describe how many different pieces are touched by changes,
and how spread those changes are.

Let's define _chunk_ (following Defects4J-Dissection[^defects4j-dissection]) as
a sequence of continuous changes in a file, consisting of the combination of
addition, removal, and modification of lines.  We will also call it a _change group_
to avoid confusion with _hunk_ as defined by (unified) diff format.

Here are all metrics that relate to the patch spread
that are calculated by `diff-annotate`:

- total number of change groups,
  i.e. contiguous spans of removed and added lines, not interrupted by context line
  (called "_number of chunks_" by Defect4J-Dissection),
- _number of modified files_
  (or rather number of different file names that occur in the diff),
- number of modified binary files, if any;
  for those files there can be no information about "lines",
  like the number of hunks, change groups (chunks), changed lines, etc.
- _spreading of chunks_ / change groups in a patch, defined[^defects4j-dissection]
  as sum over each patched file of the number of lines interleaving chunks
  in a patch; measuring how wide across file contents the patch spreads,
- sum of distances in context lines between groups (chunks) inside hunk,
  for all hunks in patched file, for all changed (patched) files,
  i.e. inner-hunk spread; this does not count context lines between hunks
  (that are mostly do not show in the patch, except for leading and trailing
  context lines in hunk)
- difference between the number of last changed line and first changed line,
  summed over changed files; this metric is computed separately for pre-image
  (source) and post-image (target) in changed files.

The last two metrics (and the number of binary files) do not appear in
Defects4J-Dissection[^defects4j-dissection] paper.

In a patch with only one chunk, the value of spreading of chunks is naturally zero,
because it represents a continuous sequence of changes. In a patch with two chunks
for a single patched file, at least one line separates the chunks. For more chunks,
naturally, this value tends to increase.  On the other hand, a patch with
two modified files has zero spreading if the patch has just two chunks,
one in each file.

It is worth noting that in Defects4J-Dissection[^defects4j-dissection] calculations
empty and comment lines were discarded for chunk spreading calculations. The
justification given in the paper is that these lines have no influence on program
behavior, and considering them would make more sense for code readability.
This is not the case for `diff-annotate` calculations, and as of version **0.4.1**
there is no option to do it (it would also slow down calculations, and very much
require access to the repository).

Defects4J-Dissection[^defects4j-dissection] paper also computes the following
patch spreading metrics, that `diff-annotate` currently does not compute:

- number of modified classes,
- number of modified methods.

Here they consider only source code files.  Those metrics are also bit specific
to Java, and they make sense only for object-oriented programming languages.

## Output format

**TODO**
