"""
ptb.py: Module for reading and transforming trees in the Penn Treebank
format.

Author: Joseph Irwin

To the extent possible under law, the person who associated CC0 with
this work has waived all copyright and related or neighboring rights
to this work.
http://creativecommons.org/publicdomain/zero/1.0/
"""


import re


LPAREN_TOKEN = object()
RPAREN_TOKEN = object()
STRING_TOKEN = object()

class Token(object):
    _token_ids = {LPAREN_TOKEN:"(", RPAREN_TOKEN:")", STRING_TOKEN:"STRING"}

    def __init__(self, token_id, value=None, lineno=None):
        self.token_id = token_id
        self.value = value
        self.lineno = lineno

    def __str__(self):
        return "Token:'{tok}'{ln}".format(
            tok=(self.value if self.value is not None else self._token_ids[self.token_id]),
            ln=(':{}'.format(self.lineno) if self.lineno is not None else '')
            )


_token_pat = re.compile(r'\(|\)|[^()\s]+')
def lex(line_or_lines):
    """
    Create a generator which returns tokens parsed from the input.

    The input can be either a single string or a sequence of strings.
    """

    if isinstance(line_or_lines, str):
        line_or_lines = [line_or_lines]

    for n,line in enumerate(line_or_lines):
        line.strip()
        for m in _token_pat.finditer(line):
            pass


def parse(line_or_lines):
    pass
