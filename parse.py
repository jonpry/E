# -*- coding: utf-8 -*-
import os
import codecs
from arpeggio import *
from arpeggio.export import PMDOTExporter
from MyPeg import *
from llvmlite import ir
from llvmlite import binding


file_name = "foo.java";

current_dir = os.path.dirname(__file__)
peg_grammar = open(os.path.join(current_dir, 'java6.peg')).read()


parser = MyPEG(peg_grammar, 'peggrammar')

#parser.debug = True
parser.skipws = False
parser.reduce_tree=False
f = codecs.open(file_name, "r", "utf-8")
test_data = f.read()
parse_tree = parser.parse(test_data)
compilation_unit = parse_tree;
#print parse_tree.__unicode__()

def flatten(_iterable):
    '''Flattening of python iterables.'''
    result = []
    for e in _iterable:
        e.parent = _iterable
        result.append(e)
        if hasattr(e, "__iter__") and not type(e) in []:
            result.extend(flatten(e))
    return result

#delete comments and other nodes related to white space
#SEMI colon never contains any information post parse
for e in flatten(parse_tree):
   if e.rule_name == u"Spacing":
      e.parent.remove(e)
   if e.rule_name == u"SEMI":
      e.parent.remove(e)

#flatten string literal as it is composed from regex
toreplace = []
for e in flatten(parse_tree):
   if e.rule_name == u"StringLiteral":
      s = ""
      for c in e:
         s += c.value
      s = s[1:-1]
      toreplace.append((e, Terminal(e.rule,e.position,s)))

for o,n in toreplace:
  index = o.parent.index(o)
  o.parent[index] = n

#flatten QI's
toreplace = []
for e in flatten(parse_tree):
   if e.rule_name == u"QualifiedIdentifier":
      s = ""
      for c in e:
         s += c.value
      toreplace.append((e, Terminal(e.rule,e.position,s)))

for o,n in toreplace:
  index = o.parent.index(o)
  o.parent[index] = n

#patch class
def is_public(self):
   for m in t.Modifier:
      if m.value == "public":
         return True
   return False
NonTerminal.is_public = is_public


#this is maybe not ideal, do we enforce the whole units must have correct filename thing?
module_name = str(compilation_unit.PackageDeclaration.QualifiedIdentifier) + "." + file_name.split(".")[0]

print "module: " + module_name

for i in compilation_unit.ImportDeclaration:
   print "import: " + str(i.QualifiedIdentifier)

#ensure one and only one public class
found_public=False
for t in compilation_unit.TypeDeclaration:
   assert t.ClassDeclaration #TODO: want to lower interface etc to classes
   if t.is_public:
      assert(not found_public)
      found_public=True;
assert(found_public)

module = ir.Module(name=module_name)
module.triple = binding.get_default_triple()


for t in compilation_unit.TypeDeclaration:
   c = t.ClassDeclaration
   name = c.Identifier.value
   for b in c.ClassBody.ClassBodyDeclaration:
     assert b.MemberDecl
     m = b.MemberDecl
     if not hasattr(m,"MethodDeclarator"):
        continue
     m = m.MethodDeclarator
     print m.Identifier.value
     ftype = ir.FunctionType(ir.VoidType(), [ir.DoubleType(),ir.DoubleType()], False)
     func = ir.Function(module, ftype, m.Identifier.value)
     block = func.append_basic_block('entry')
     builder = ir.IRBuilder(block)
     a, b = func.args
     result = builder.fadd(a, b, name="res")
     builder.ret_void()

print str(module)

