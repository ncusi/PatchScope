from textwrap import dedent

import pygments
from pygments.lexer import Lexer as PygmentsLexer

from lexer import Lexer

LEXER = Lexer()


def test_get_lexer():
    ## DEBUG
    # pprint.pp(inspect.getclasstree(inspect.getmro(pygments.lexers.CLexer)))

    lex_c = LEXER.get_lexer('main.c')
    # NOTE: for some reason pygments.lexer.Lexer did not work here
    # AttributeError: module 'pygments' has no attribute 'lexer'
    assert isinstance(lex_c, PygmentsLexer), \
        "got a lexer"
    assert isinstance(lex_c, pygments.lexers.CLexer), \
        "got a C lexer"

    another_lex_c = LEXER.get_lexer('src/stats.c')
    assert another_lex_c == lex_c, \
        "got cached lexer"


def test_lex():
    example_C_code = dedent('''\
     /**
      * brief       Calculate approximate memory requirements for raw encoder
      *
      */
      int i = 1; /* an int */''')
    # NOTE: currently forcing it to a list is not necessary
    tokens = list(LEXER.lex(filename='main.c', code=example_C_code))

    assert len(tokens[0]) == 3, \
        "lex returns iterable of 3-element tuples"
    assert tokens[0][0] == 0, \
        "lex first token starts at position 0 in source"

    concat = ''.join([elem[2] for elem in tokens])
    assert concat == example_C_code, \
        "lex parses all source code, and it is recoverable from tokens"
