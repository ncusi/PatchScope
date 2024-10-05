import logging
from pathlib import Path
from typing import Dict, Tuple, Iterable

import pygments
from pygments.lexer import Lexer as PygmentsLexer
from pygments import lexers, util


# support logging
logger = logging.getLogger(__name__)


class Lexer(object):
    """Holder and proxy for lexers

    Made to be able to reuse lexer objects, and to call the lexing method
    required by the :meth:`AnnotatedHunk.process()` method.
    """

    def __init__(self):
        """Construct the Lexer object, creating the holder for lexers"""
        self.lexers: Dict[str, PygmentsLexer] = {}

    def get_lexer(self, filename: str) -> PygmentsLexer:
        """Get lexer suitable for file with given path

        :param filename: path to a file inside repository
        :return: appropriate lexer
        """
        suffix = Path(filename).suffix
        # there are many different file types with an empty suffix
        if not suffix:
            # use basename of the file as key in self.lexers
            suffix = Path(filename).name

        if suffix in self.lexers:
            return self.lexers[suffix]

        try:
            lexer = pygments.lexers.get_lexer_for_filename(filename)
        except pygments.util.ClassNotFound:
            logger.warning(f"Warning: No lexer found for '{filename}', trying Text lexer")
            # TODO: use Text lexer directly: pygments.lexers.special.TextLexer
            lexer = lexers.get_lexer_for_filename("Test.txt")

        self.lexers[suffix] = lexer

        return lexer

    def lex(self, filename: str, code: str) -> Iterable[Tuple]:
        """Run lexer on a fragment of code from file with given filename

        :param filename: path to file within the repository
        :param code: source code or text to parse
        :return: an iterable of (index, token_type, text_fragment) tuples
        """
        lexer = self.get_lexer(filename)

        if not lexer:
            logger.error(f"Error in lex: no lexer selected for file '{filename}'")
            return []

        # TODO: consider returning generator or iterator, instead of iterable/list
        return list(lexer.get_tokens_unprocessed(code))
