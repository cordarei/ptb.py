#!/usr/bin/env python

"""
Usage: print-s.py FILE

Print the top-level structure of parse trees in FILE
"""

from sexp import sexps, tokenize, isterminal

import re
import sys

filename = sys.argv[1]

def remove_coindex(s):
    return re.sub('-\d+$', '', s)

for i,sexp in enumerate(sexps(tokenize(open(filename)))):
    if isinstance(sexp, list) and len(sexp) == 1:
        sexp = sexp[0]
    assert(isinstance(sexp[0], str))
    children = sexp[1:]
    print(
        sexp[0],
        '=>',
        ' '.join(
            ('{1}/{0}'.format(*c) if isterminal(c) else remove_coindex(c[0]))
            for c in children
            )
    )
