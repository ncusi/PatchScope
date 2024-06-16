import collections.abc
from collections import defaultdict, deque
import re
from typing import List, Dict, Tuple, TypeVar
from typing import Iterable, Generator  # should be imported from collections.abc

from pygments.token import Token


T = TypeVar('T')
TRANSLATION_TABLE = str.maketrans("", "", "*/\\\t\n")


def line_ends_idx(text: str) -> List[int]:
    """Return position+1 for each newline in text

    This way each line can be extracted with text[pos[i-1]:pos[i]].

    >>> text = "123\\n56\\n"
    >>> line_ends_idx(text)
    [4, 7]
    >>> text[0:4]
    '123\\n'
    >>> text[4:7]
    '56\\n'

    :param text: str to process
    :return: list of positions after end of line characters
    """
    return [i for i, ch in enumerate(text, start=1)
            if ch == '\n']


def split_multiline_lex_tokens(tokens_unprocessed: Iterable[T]) -> Generator[T, None, None]:
    """Split multiline tokens into individual lines

    :param tokens_unprocessed: Result of calling `get_tokens_unprocessed(text)`
        method on a `pygments.lexer.Lexer` instance.  This is an iterable
        of (index, token_type, value) tuples, where index is the starting
        position of the token within the input text.

    :return: An iterable of (index, token_type, value) tuples, where `index`
        is the starting position of `value` in the input text, and each
        `value` contains at most one newline.
    """
    for index, token_type, text_fragment in tokens_unprocessed:
        lines = text_fragment.splitlines(keepends=True)

        if len(lines) <= 1:
            # no need for splitting, return original
            yield index, token_type, text_fragment
        else:
            # split into lines, updating the index
            running_count = 0
            for line in lines:
                yield index+running_count, token_type, line
                running_count += len(line)


def group_tokens_by_line(code: str, tokens: Iterable[T]) -> Dict[int, List[T]]:
    """Group tokens by line in code

    For each line in the source `code`, find all `tokens` that belong
    to that line, and group tokens by line.  **Note** that `tokens` must
    be result of parsing `code`.

    :param code: Source code text that was parsed into tokens
    :param tokens: An iterable of (index, token_type, value) tuples,
        preferably with `value` split into individual lines with the
        help of `split_multiline_lex_tokens` function.
    :return: mapping from line number in `code` to list of tokens
        in that line
    """
    tokens_deque = deque(tokens)
    idx_code = line_ends_idx(code)

    line_tokens = defaultdict(list)
    for no, idx in enumerate(idx_code):
        while tokens_deque:
            token = tokens_deque.popleft()
            if token[0] < idx:
                line_tokens[no].append(token)
            else:
                tokens_deque.appendleft(token)
                break

    return line_tokens


def front_fill_gaps(data: Dict[int, T]) -> Dict[int, T]:
    """Fill any gaps in `data` keys with previous value

    >>> front_fill_gaps({1: '1', 3: '3'})
    {1: '1', 2: '1', 3: '3'}

    :param data: Input data - dictionary with int keys
    :return: Front filled input data
    """
    if not data:
        return {}

    # Find the minimum and maximum keys
    min_key = min(data.keys())
    max_key = max(data.keys())

    # Create a new dictionary to store the result
    filled_dict = {}

    # Initialize the previous value
    previous_value = None

    # Iterate through the range of keys
    for key in range(min_key, max_key + 1):
        if key in data:
            previous_value = data[key]
        filled_dict[key] = previous_value

    return filled_dict


def deep_update(d: dict, u: collections.abc.Mapping) -> dict:
    """Update nested dictionary of varying depth

    Update dict `d` with the contents of dict `u`, without overwriting
    deeply nested levels in input dictionary `d`.  **Note** that this
    would also extend `d` with new keys from `u`.

    :param d: dict to update
    :param u: data to update with
    :return: updated input dict
    """
    # modified from https://stackoverflow.com/a/3233356/46058
    # see also https://github.com/pydantic/pydantic/blob/v2.7.4/pydantic/_internal/_utils.py#L103
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = deep_update(d.get(k, {}), v)
        elif isinstance(v, collections.abc.MutableSequence):
            list_value = d.get(k, [])
            list_value.extend(v)
            d[k] = list_value
        else:
            d[k] = v

    return d


def clean_text(text: str) -> str:
    ret = text.translate(TRANSLATION_TABLE)
    ret = re.sub(pattern=r'\s+', repl=' ', string=ret)
    return ret


def line_is_comment(tokens_list: Iterable[Tuple]) -> bool:
    """Given results of parsing line, find if it is comment

    :param tokens_list: An iterable of (index, token_type, text_fragment) tuples,
        supposedly from parsing some line of source code text
    :return: Whether set of tokens in `tokens_list` can be all
        considered to be a comment
    """
    can_be_comment = False
    cannot_be_comment = False

    for _, token_type, text_fragment in tokens_list:
        if token_type in Token.Comment:
            can_be_comment = True
        elif token_type in Token.Text.Whitespace:
            # white space in line is also ok
            can_be_comment = True
        elif token_type in Token.Text and text_fragment.isspace():
            # white space in line is also ok
            can_be_comment = True
        else:
            # other tokens
            cannot_be_comment = True
            break

    return can_be_comment and not cannot_be_comment
