#!/usr/bin/env python

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import ptb

def expectequal(a,b):
    assert a == b, '\n{}\n{}'.format(a,b)

if __name__ == '__main__':
    tree = """( (S (S-TPC-1 (NP-SBJ (PRP xx) ) (ADVP (RB xx) ) (VP (VBZ xx) (NP-PRD (DT xx) (NN xx) (NN xx) ))) (, ,) (NP-SBJ (NNS xx) ) (VP (VBP xx) (SBAR (-NONE- 0) (S (-NONE- *T*-1) ))) (. .) ))"""
    transformed_tree = """(ROOT (S (S (NP (PRP xx) ) (ADVP (RB xx) ) (VP (VBZ xx) (NP (DT xx) (NN xx) (NN xx) ))) (, ,) (NP (NNS xx)) (VP (VBP xx)) (. .) ))"""
    spans = [
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
    ]

    t = next(ptb.parse(tree))
    u = next(ptb.parse(transformed_tree))

    expectequal( set(spans) , set(ptb.all_spans(t)) )

    ptb.remove_empty_elements(t)
    ptb.simplify_labels(t)
    t = ptb.add_root(t)
    expectequal( set(ptb.all_spans(t)) , set(ptb.all_spans(u)) )
