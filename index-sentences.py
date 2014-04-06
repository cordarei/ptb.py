#!/usr/bin/env python

"""
Usage: index-sentences.py FILE

print an index of the parsed sentences in FILE
"""

from sexp import sexps, tokenize, stringify, terminals


def index_sentences(filename):
    for i,sexp in enumerate(sexps(tokenize(open(filename)))):
        print('{file}|{sent}|{len}|{sexp}'.format(
            file=filename,
            sent=i,
            len=len(list(terminals(sexp))),
            sexp=stringify(sexp)))


def main():
    import sys
    filename = sys.argv[1]
    try:
        index_sentences(filename)
        #print_tokens(filename)
        #print_tokens(filename, include_nulls=True)
    except:
        print("Error while processing file:", filename, file=sys.stderr)
        raise


main()
