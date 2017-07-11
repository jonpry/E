# -*- coding: utf-8 -*-
import os
import codecs
import json
from collections import OrderedDict
from sets import Set
from arpeggio import *
from arpeggio.export import PMDOTExporter
from MyPeg import *
from llvmlite import ir
from llvmlite import binding
import emit

def to_json(n, d):
    '''Convert a PEG parse tree into JSON'''
    rule_name = n.rule.name.split("=")[0].split("(")[0];

    if type(n) == NonTerminal:
       nd = OrderedDict()
       for e in n:
          to_json(e,nd)
       to_insert = nd
    else:
       to_insert = n.value

    if rule_name in d:
       d[rule_name].append(to_insert)
    else:
       d[rule_name] = [to_insert]


def parse_file(file_name):
  current_dir = os.path.dirname(__file__)
  peg_grammar = open(os.path.join(current_dir, 'java6.peg')).read()


  parser = MyPEG(peg_grammar, 'peggrammar')

  #parser.debug = True
  parser.skipws = False
  parser.reduce_tree=False
  f = codecs.open(file_name, "r", "utf-8")
  test_data = f.read()
  parse_tree = parser.parse(test_data)
  s = OrderedDict()
  to_json(parse_tree,s)

  #print json.dumps(s)

  return s

def rule_match_one(position, rules, has_one=False):
    rule = rules[0]
    if position[0].split("[")[0] == rule:
       if len(rules) > 1:
           if len(position) > 1:
             return rule_match_one(position[1:],rules[1:])
           return False
       return True
    return False

def rule_match(position, rules):
    #print (position, rules)
    for i in range(len(position)):
        if rule_match_one(position[i:], rules):
           #print "match"
           return True
    return False   

def navigate((k,v),stack,rule,matches):
    if k[0] == '[':
       stack[len(stack)-1] = stack[len(stack)-1] + k
    else:
       stack.append(k)

    #TODO: unclear if this is a good idea
    if rule_match(stack,rule):
       matches.append(stack[:])
       stack.pop()
       return
    if isinstance(v,OrderedDict):
       for k2,v2 in v.items():
          navigate((k2,v2),stack,rule,matches)
       stack[len(stack)-1] = stack[len(stack)-1].split("[")[0]
    elif isinstance(v,list):
       idx = 0
       for v2 in v:
          navigate((u"[" + str(idx) + "]",v2),stack,rule,matches)
          idx += 1
       stack.pop()

def navigate_all(parse_tree,rule):
    matches = []
    navigate(parse_tree.items()[0],[],rule,matches)
    #print matches
    return matches

def parse_rule(rule):
    rules = rule.split(".")
    return rules

def get_node(parse_tree,location):
    #print type(parse_tree)
    if isinstance(parse_tree,OrderedDict):
       if len(location) == 1:
          return parse_tree[location[0]]
       return get_node(parse_tree[location[0]],location[1:])
    if isinstance(parse_tree,list):
       if len(location) == 1:
          return parse_tree[int(location[0][1:-1])]
       return get_node(parse_tree[int(location[0][1:-1])],location[1:])

    assert(False)

def expand_position(position):
    ret = []
    for p in position:
      a = p.split("[")
      ret.append(a[0])
      if len(a) > 1:
        ret.append("[" + a[1])
    return ret

def delete_node(parse_tree,position,rule):
    position = expand_position(position)
    parent = get_node(parse_tree,position[:-1]) #find parent
    node = get_node(parent,position[len(position)-1:]) #find parent
    #TODO: handle dict and array
    #TODO: perform delete operations after all references obtained
    del parent[position[len(position)-1]]

def reparent_node(parse_tree,position,rule):
    position = expand_position(position)
    dparent = get_node(parse_tree,position[:-2]) #find parent
    parent = get_node(parse_tree,position[:-1]) #find parent
    #print dparent

    if len(parent) > 1:
      return

    for i in range(len(dparent)):
      if dparent[i] == parent:
        dparent[i] = parent.items()[0][1][0]
        break

def uniqify(d):
   nd = OrderedDict()
   #print d
   for e in d:
      for k,v in e.items():
        if k in nd:
          nd[k].append(v)
        else:
          nd[k] = v
   return nd

foo=0
''' If one of my children is not an array then delete me'''
def test_and_reparent(parse_tree,position,rule):
    global foo
    print rule
    isit = False
    if rule[0] == "MultiplicativeExpression":
      foo += 1
      if foo == 2:
        isit = True

    position = expand_position(position)
    dparent = get_node(parse_tree,position[:-2]) #find parent
    parent = get_node(parse_tree,position[:-1]) #find parent
    node = get_node(parse_tree,position) #find parent

    found = False
    for n in node:
       for k,v in n.items():
          if len(v) > 1:
             found = True
             break
       print found

    if found:
      return 

    if isit:
      print json.dumps(dparent) + ", " + str(found)
      #print json.dumps(parent) + ", " + str(found)

    for i in range(len(dparent)):
      if dparent[i] == parent:
         dparent[i] = uniqify(parent.items()[0][1])
         print ""
         print json.dumps(uniqify(parent.items()[0][1]))
         print json.dumps(parent.items()[0][1])

    if isit:
      print json.dumps(dparent) + ", " + str(found)
      #print json.dumps(parent) + ", " + str(found)
      

    
def assemble_qi(parse_tree,position,rule):
    position = expand_position(position)
    node = get_node(parse_tree,position) #find parent
    idx = 0
    #print json.dumps(node)
    for qi in node:
      si = qi["Identifier"][0]
      if "DotIdentifier" in qi:
        for di in qi["DotIdentifier"]:
          si += "." + di["Identifier"][0]
      node[idx] = si
      idx += 1

def assemble_sl(parse_tree,position):
    position = expand_position(position)
    node = get_node(parse_tree,position) #find parent
    idx = 0
    #print json.dumps(node)
    for sl in node:
      chars = sl["_"]
      si = ""
      for c in chars:
        si += c
      print si
      node[idx] = si
      idx += 1
    #print json.dumps(node)

    #exit(0)


def execute_rule(parse_tree, rule):
   matches = navigate_all(parse_tree,parse_rule(rule[0]))
   for match in matches:
     rule[1](parse_tree,match,rule)

keywords = ["AT", "AND", "ANDAND", "ANDEQU", "BANG", "BSR", "BSREQU", "COLON", 
            "COMMA", "DEC", "DIV", "DIVEQU", "DOT", "ELLIPSIS", "EQU", "EQUAL", 
            "GE", "GT", "HAT", "HATEQU", "INC", "LBRK", "LE", "LPAR", "LPOINT", 
            "LT", "LWING", "MINUS", "MINUSEQU", "MOD", "MODEQU", "NOTEQUAL", 
            "OR", "OREQU", "OROR", "PLUS", "PLUSEQU", "QUERY", "RBRK", "RPAR", 
            "RPOINT", "RWING", "SEMI", "SL", "SLEQU", "SR", "SREQU", "STAR"
            "STAREQU", "TILDA"]

def compact(item):
   if isinstance(item,OrderedDict):
      nd = OrderedDict()
      for k,v in item.items():
         nd[k] = compact(v)
      return nd
   elif isinstance(item,list):
      if len(item) == 1:
         return compact(item[0])
      na = []
      for e in item:
         na.append(compact(e))
      return na
   return item

def pretty_print(tree):
   #ntree = compact(tree)
   print json.dumps(tree,indent=1)


def main():
    '''First pass, condensation'''
    rules = [(u"Spacing",			delete_node),
             (u"SEMI",				delete_node),
             (u"StringLiteral", 		assemble_sl),
             (u"RegExMatch",			reparent_node),
             (u"StrMatch",			reparent_node),
             (u"QualifiedIdentifier",		assemble_qi)]

    parse_tree = parse_file("foo.java");

    #pretty_print(parse_tree)

    for rule in rules:
        execute_rule(parse_tree,rule)

    #pretty_print(parse_tree)
    
    '''Second pass, lowering'''

    '''Third pass, emit declarations'''
    emit.emit_module(parse_tree["CompilationUnit"][0],"decl_only")

    '''Fourth pass, emit definitions'''
    emit.emit_module(parse_tree["CompilationUnit"][0],"method_body")

main()

