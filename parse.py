# -*- coding: utf-8 -*-
import os
import codecs
from arpeggio import *
from arpeggio.export import PMDOTExporter
from MyPeg import *

current_dir = os.path.dirname(__file__)
peg_grammar = open(os.path.join(current_dir, 'java6.peg')).read()


parser = MyPEG(peg_grammar, 'peggrammar')
print parser

#parser.debug = True
parser.skipws = False
#parser.reduce_tree=True
f = codecs.open("foo2.java", "r", "utf-8")
test_data = f.read()
parse_tree = parser.parse(test_data)

print parse_tree.PackageDeclaration.rule.nodes[0].id

print parse_tree.__unicode__()


