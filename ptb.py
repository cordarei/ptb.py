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
            if m.group() == '(':
                yield Token(LPAREN_TOKEN)
            elif m.group() == ')':
                yield Token(RPAREN_TOKEN)
            else:
                yield Token(STRING_TOKEN, value=m.group())


class Symbol:
    _pat = re.compile(r'(?P<label>^[^0-9=-]+)|(?:-(?P<tag>[^0-9=-]+))|(?:=(?P<parind>[0-9]+))|(?:-(?P<coind>[0-9]+))')
    def __init__(self, label):
        self.label = label
        self.tags = []
        self.coindex = None
        self.parindex = None
        for m in self._pat.finditer(label):
            if m.group('label'):
                self.label = m.group('label')
            elif m.group('tag'):
                self.tags.append(m.group('tag'))
            elif m.group('parind'):
                self.parindex = m.group('parind')
            elif m.group('coind'):
                self.coindex = m.group('coind')

class Word:
    def __init__(self, word, pos):
        self.word = word
        self.pos = pos

class Texpr:
    def __init__(self, head, tail):
        self.head = head
        self.tail = tail

    def symbol(self):
        if hasattr(self.head, 'label'):
            return self.head
        else:
            return None

    def children(self):
        if self.symbol() is not None:
            t = self.tail
            while t is not None:
                yield t
                t = t.tail

    def word(self):
        if hasattr(self.head, 'pos'):
            return self.head.word
        else:
            return None

    def tag(self):
        try:
            return self.head.pos
        except AttributeError:
            return None


def parse(line_or_lines):
    def istok(t, i):
        return getattr(t, 'token_id', None) is i
    stack = []
    for tok in lex(line_or_lines):
        if tok.token_id is LPAREN_TOKEN:
            stack.append(tok)
        elif tok.token_id is STRING_TOKEN:
            stack.append(tok)
        else:
            if (istok(stack[-1], STRING_TOKEN) and
                istok(stack[-2], STRING_TOKEN) and
                istok(stack[-3], LPAREN_TOKEN)):
                w = Word(stack[-1].value, stack[-2].value)
                stack.pop()
                stack.pop()
                stack.pop()
                stack.append(w)
            else:
                tail = None
                while not istok(stack[-1], LPAREN_TOKEN):
                    head = stack.pop()
                    if istok(head, STRING_TOKEN):
                        head = Symbol(head.value)
                    tail = Texpr(head, tail)
                stack.pop()
                if not stack:
                    yield tail
                else:
                    stack.append(tail)
