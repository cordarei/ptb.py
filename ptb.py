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


#######
# Utils
#######

def gensym():
    return object()


##################
# Lexer
##################


LPAREN_TOKEN = gensym()
RPAREN_TOKEN = gensym()
STRING_TOKEN = gensym()

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

class Leaf:
    def __init__(self, word, pos):
        self.word = word
        self.pos = pos

class TExpr:
    def __init__(self, head, first_child, next_sibling):
        self.head = head
        self.first_child = first_child
        self.next_sibling = next_sibling

    def symbol(self):
        if hasattr(self.head, 'label'):
            return self.head
        else:
            return None

    def children(self):
        n = self.first_child
        while n is not None:
            yield n
            n = n.next_sibling

    def leaf(self):
        if hasattr(self.head, 'pos'):
            return self.head
        else:
            return None

    def __str__(self):
        if self.leaf():
            return '({} {})'.format(self.leaf().pos, self.leaf().word)
        else:
            return '({} {})'.format(
                self.head if self.head is not None else '',
                ' '.join(str(c) for c in self.children())
            )


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
                w = Leaf(stack[-1].value, stack[-2].value)
                stack.pop()
                stack.pop()
                stack.pop()
                stack.append(TExpr(w, None, None))
            else:
                tx = None
                tail = None
                while not istok(stack[-1], LPAREN_TOKEN):
                    head = stack.pop()
                    if istok(head, STRING_TOKEN):
                        tx = TExpr(
                            Symbol(head.value),
                            first_child = tail,
                            next_sibling = None
                        )
                    else:
                        head.next_sibling = tail
                        tail = head
                stack.pop()
                if tx is None:
                    tx = TExpr(None, tail, None)
                if not stack:
                    yield tx
                else:
                    stack.append(tx)


##################
# Traversal
##################

def traverse(tx, pre=None, post=None, state=None):
    """
    Traverse a tree.

    Allows pre-, post-, or full-order traversal. If given, `pre` and
    `post` should be functions or callable objects accepting two
    arguments: a TExpr node and a state object. If the state is used,
    `pre` and `post` should return a new state object.
    """
    if pre is not None:
        state = pre(tx, state)
    for c in tx.children():
        state = traverse(c, pre, post, state)
    if post is not None:
        state = post(tx, state)
    return state


##################
# Transforms
##################


def remove_empty_elements(tx):
    q_none = gensym()
    q_ok = gensym()
    state = [[]]

    def pre(tx, st):
        if tx.leaf() is None:
            return st + [[]]
        else:
            return st

    def post(tx, st):
        q = q_ok
        if tx.leaf():
            q = q_none if tx.leaf().pos == '-NONE-' else q_ok
        else:
            cs = st.pop()
            cs = [c for q,c in cs if q is q_ok]
            if cs:
                tx.first_child = cs[0]
                for c,d in zip(cs[:-1],cs[1:]):
                    c.next_sibling = d
                cs[-1].next_sibling = None
            else:
                q = q_none
        st[-1].append( (q, tx) )
        return st

    state = traverse(tx, pre, post, state)


def simplify_labels(tx):
    def proc(tx, st):
        if tx.symbol():
            tx.symbol().simplify()
    traverse(tx, proc)


_dummy_labels = ('ROOT', 'TOP')
def add_root(tx, root_label='ROOT'):
    if (tx.head is None or (tx.symbol() and tx.symbol().label in _dummy_labels)):
        tx.head = Symbol(root_label)
    else:
        tx = TExpr(Symbol(root_label), tx)
    return tx


##################
# Other Useful Functions
##################


def all_spans(tx):
    """
    Returns a list of spans in a tree. The spans are in depth-first
    traversal order.
    """
    state = ([], [], 0, 0)

    def pre(tx, st):
        spans, stack, begin, count = st
        return (
            spans,
            stack + [(count, begin)],
            begin,
            count + 1
        )

    def post(tx, st):
        spans, stack, end, count = st
        num, begin = stack.pop()

        label = None
        if tx.leaf():
            if tx.leaf().pos != '-NONE-':
                end = begin + 1
            label = tx.leaf().pos
        elif tx.symbol():
            label = str(tx.symbol())

        if label:
            spans.append((num, (label, begin, end)))

        return (
            spans,
            stack,
            end,
            count
        )

    spans, _, _, _ = traverse(tx, pre, post, state)
    spans.sort()
    return [s for n,s in spans]


##################
# Parse Tree
##################

class Span(object):
    def __init__(self, label, begin, end):
        self.label = label
        self.begin = begin
        self.end = end

    def tojson(self):
        return [str(self.label), self.begin, self.end]


class GroundedTree(object):
    def __init__(self, span, children):
        self.span = span
        self.children = children

    def tojson(self):
        return {
            "head" : self.span.tojson(),
            "children" : [c.tojson() for c in self.children]
        }


class ParsedSentence(object):
    def __init__(self, terminals, tree):
        self.terminals = terminals
        self.tree = tree

    def _index(self, begin_or_span=0, end=None):
        b = begin_or_span
        try:
            if end is None:
                return self.terminals[b:]
            else:
                return self.terminals[b:end]
        except TypeError:
            try:
                return self.terminals[b.span.begin:b.span.end]
            except AttributeError:
                return self.terminals[b.begin:b.end]

    def words(self, begin_or_span=0, end=None):
        for t in self._index(begin_or_span, end):
            yield t.word

    def tagged_words(self, begin_or_span=0, end=None):
        for t in self._index(begin_or_span, end):
            yield (t.pos, t.word)

    def tags(self, begin_or_span=0, end=None):
        for t in self._index(begin_or_span, end):
            yield t.pos

    def tojson(self):
        return {
            "parse" : self.tree.tojson(),
            "words" : [t.word for t in self.terminals],
            "tags" : [t.pos for t in self.terminals]
        }


TERMINAL_NODE_LABEL = '<t>'
def make_grounded(tx):
    state = ([([], 0)], 0)

    def pre(tx, st):
        stack, begin = st
        return (
            stack + [([], begin)],
            begin
        )

    def post(tx, st):
        stack, end = st
        children, begin = stack.pop()
        if tx.leaf():
            end += 1
        grounded = GroundedTree(
            Span(
                tx.symbol() or TERMINAL_NODE_LABEL,
                begin,
                end
            ),
            children
        )
        stack[-1][0].append(grounded)
        return (stack, end)

    stack, _ = traverse(tx, pre, post, state)
    gs, _ = stack[0]
    return gs[0]

def leaves(tx):
    def proc(tx, st):
        return st + ([tx.leaf()] if tx.leaf() else [])
    return traverse(tx, proc, state=[])

def make_parsed_sent(tx):
    return ParsedSentence(leaves(tx), make_grounded(tx))

##################
# Tests
##################


def dotests():
    def expectequal(a,b):
        assert a == b, '\n{}\n{}'.format(a,b)

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

    expectequal( set(spans[0]) , set(all_spans(t)) )

    remove_empty_elements(t)
    simplify_labels(t)
    t = add_root(t)
    expectequal( set(all_spans(t)) , set(all_spans(u)) )


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
        dotests()

if __name__ == "__main__":
    import sys
    main(sys.argv[1:])
