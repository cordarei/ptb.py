#!/usr/bin/env python

"""
ptb.py: Module for reading and transforming trees in the Penn Treebank
format.

Author: Joseph Irwin

To the extent possible under law, the person who associated CC0 with
this work has waived all copyright and related or neighboring rights
to this work.
http://creativecommons.org/publicdomain/zero/1.0/
"""


from __future__ import print_function

import re


##################
# Lexer
##################


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


##################
# Parser
##################


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

    def simplify(self):
        self.tags = []
        self.coindex = None
        self.parindex = None

    def __str__(self):
        return '{}{}{}{}'.format(
            self.label,
            ''.join('-{}'.format(t) for t in self.tags),
            ('={}'.format(self.parindex) if self.parindex is not None else ''),
            ('-{}'.format(self.coindex) if self.coindex is not None else '')
        )

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

    def __str__(self):
        if self.word():
            return '({} {})'.format(self.tag(), self.word())
        elif self.symbol():
            return '({} {})'.format(
                self.head,
                ' '.join(
                    str(c if c.word() or c.symbol() else c.head)
                    for c in self.children()
                )
            )
        else:
            return '({})'.format(self.head)


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


##################
# Transforms
##################


def remove_empty_elements(tx):
    if tx.word():
        if tx.tag() == '-NONE-':
            tx.head = None
    elif tx.symbol():
        n = tx
        while n.tail is not None:
            m = n.tail
            remove_empty_elements(m)
            if m.head is None:
                n.tail = m.tail
            else:
                n = n.tail
        if tx.tail is None:
            tx.head = None
    else:
        remove_empty_elements(tx.head)
        if tx.head.head is None:
            tx.head = None


def simplify_labels(tx):
    if tx.symbol():
        tx.symbol().simplify()
        for c in tx.children():
            simplify_labels(c)
    elif tx.word() is None:
        simplify_labels(tx.head)


_dummy_labels = ('ROOT', 'TOP')
def add_root(tx, root_label='ROOT'):
    if tx.symbol() is None and tx.tail is None:
        return Texpr(Symbol(root_label), tx)
    elif tx.symbol() and tx.symbol().label in _dummy_labels:
        return Texpr(Symbol(root_label), tx.tail)
    else:
        return Texpr(Symbol(root_label), Texpr(tx, None))


##################
# Traversal
##################

def _all_spans(tx, begin=0):
    if not tx.symbol() and not tx.tag():
        tx = tx.head

    end = begin
    if tx.symbol():
        for c in tx.children():
            for span, b2, end in _all_spans(c, end):
                yield (span, b2, end)
        yield (str(tx.symbol()), begin, end)
    elif tx.tag():
        if tx.tag() != '-NONE-':
            end += 1
        yield (tx.tag(), begin, end)

# def _all_spans(tx):
#     def succ(t):
#         return list(t.children())[::-1]
#     if tx.symbol() is None and tx.tag() is None:
#         tx = tx.head
#     stack = [(tx, 0, succ(tx))]
#     state = 0
#     while stack:
#         if stack[-1][2]:
#             t = stack[-1][2].pop()
#             if t.symbol() is None and t.tag() is None:
#                 t = t.head
#             stack.append( (t, state, succ(t)) )
#         else:
#             t, begin, _ = stack.pop()
#             if t.tag() and t.tag() != '-NONE-':
#                 state += 1
#             end = state
#             span = (str(t.symbol()) if t.symbol() else t.tag())
#             yield (span, begin, end)

def all_spans(tx):
    """
    Returns a list of spans in a tree. The spans are ordered so that
    children follow their parents. However, 'empty' elements (e.g.
    '-NONE-') may not be sorted correctly.
    """
    spans = list(_all_spans(tx, 0))
    spans.reverse()
    spans.sort(key=lambda x: (x[1], 1 if x[2] > x[1] else 0, -x[2]))
    return spans


##################
# Tests
##################


def runtests():
    test = (
        """( (S (S-TPC-1 (NP-SBJ (PRP xx) ) (ADVP (RB xx) ) (VP (VBZ xx) (NP-PRD (DT xx) (NN xx) (NN xx) ))) (, ,) (NP-SBJ (NNS xx) ) (VP (VBP xx) (SBAR (-NONE- 0) (S (-NONE- *T*-1) ))) (. .) ))""",
        """(ROOT (S (S (NP (PRP xx) ) (ADVP (RB xx) ) (VP (VBZ xx) (NP (DT xx) (NN xx) (NN xx) ))) (, ,) (NP (NNS xx)) (VP (VBP xx)) (. .) ))"""
    )
    spans = (
        [
            ('S', 0, 10),
            ('S-TPC-1', 0, 6),
            ('NP-SBJ', 0, 1),
            ('PRP', 0, 1),
            ('ADVP', 1, 2),
            ('RB', 1, 2),
            ('VP', 2, 6),
            ('VBZ', 2, 3),
            ('NP-PRD', 3, 6),
            ('DT', 3, 4),
            ('NN', 4, 5),
            ('NN', 5, 6),
            (',', 6, 7),
            ('NP-SBJ', 7, 8),
            ('NNS', 7, 8),
            ('VP', 8, 9),
            ('VBP', 8, 9),
            ('SBAR', 9, 9),
            ('S', 9, 9),
            ('-NONE-', 9, 9),
            ('-NONE-', 9, 9),
            ('.', 9, 10)
        ],
    )
    t = next(parse(test[0]))
    u = next(parse(test[1]))

    assert set(spans[0]) == set(all_spans(t))

    remove_empty_elements(t)
    simplify_labels(t)
    t = add_root(t)
    assert set(all_spans(t)) == set(all_spans(u))


##################
# Main
##################


def main(args):
    """
    Usage:
      ptb process [options] [--] <file>
      ptb dump_sentences [--] <file>
      ptb test
      ptb -h | --help

    Options:
      --add-root                Add a root node to the tree.
      -r=ROOT --root=ROOT       Specify label of root node. [default: ROOT]
      --simplify-labels         Simplify constituent labels.
      --remove-empties          Remove empty elements.
      -h --help                 Show this screen.
    """
    from docopt import docopt
    args = docopt(main.__doc__, argv=args)

    def trees():
        if args['<file>'] == '-':
            for t in parse(sys.stdin):
                yield t
        else:
            with open(args['<file>'], 'r') as f:
                for t in parse(f):
                    yield t

    if args['process']:
        for t in trees():
            if args['--remove-empties']:
                remove_empty_elements(t)
            if args['--simplify-labels']:
                simplify_labels(t)
            if args['--add-root']:
                t = add_root(t, root_label=args['--root'])
            print(t)

    if args['dump_sentences']:
        for t in trees():
            remove_empty_elements(t)
            t = add_root(t)
            t = next(t.children())
            stack = [t]
            words = []
            while stack:
                t = stack.pop()
                if not t.symbol() and not t.word():
                    t = t.head
                if t.word():
                    words.append(t.word())
                else:
                    stack.extend(reversed(list(t.children())))
            print(' '.join(words))

    if args['test']:
        runtests()

if __name__ == "__main__":
    import sys
    main(sys.argv[1:])
