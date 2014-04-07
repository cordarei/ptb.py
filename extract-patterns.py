#!/usr/bin/env python

"""
Usage: extract-patterns.py FILE

Print patterns in the structure of parse trees in FILE
"""

from sexp import sexps, tokenize, isterminal

import re
import sys

filename = sys.argv[1]

def remove_coindex(s):
    return re.sub('-\d+$', '', s)

def get_verb(sexp):
    if isterminal(sexp):
        if sexp[0][0] == 'V':
            return sexp[1]
    else:
        vs = [get_verb(c) for c in sexp[1:] if c[0][0] == 'V']
        if vs:
            return vs[-1]

def isreportverb(vb):
    return vb in ["say",
                  "says",
                  "said",
                  "announced",
                  "announce",
                  "announces"]

def format_constituent(sexp):
    if isterminal(sexp):
        return '{1}/{0}'.format(*sexp)
    else:
        l = remove_coindex(sexp[0])
        v = get_verb(sexp)
        if isreportverb(v):
            return '{0}/{1}'.format(l, v)
        else:
            return l

for i,sexp in enumerate(sexps(tokenize(open(filename)))):
    if isinstance(sexp, list) and len(sexp) == 1:
        sexp = sexp[0]
    assert(isinstance(sexp[0], str))
    children = sexp[1:]
    print(
        sexp[0],
        '=>',
        ' '.join(
            format_constituent(c)
            #('{1}/{0}'.format(*c) if isterminal(c) else remove_coindex(c[0]))
            for c in children
            )
    )
