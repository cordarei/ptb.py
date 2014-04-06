#!/usr/bin/env python

"""
Usage: add-root.py FILE

Add a dummy ROOT label to the top of every parse tree in FILE
"""

from sexp import sexps, tokenize, isterminal, stringify

import sys

filename = sys.argv[1]

for i,sexp in enumerate(sexps(tokenize(open(filename)))):
    if isinstance(sexp, list) and len(sexp) == 1:
        sexp = sexp[0]
    print(stringify(['ROOT', sexp]))
    print()
