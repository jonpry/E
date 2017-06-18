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

def emit_integer_literal(il,builder): 
   val = int(il["DecimalNumeral"][0])
   return ir.Constant(ir.IntType(32), val)

def emit_literal(l,builder):
   if "IntegerLiteral" in l:
       return emit_integer_literal(l["IntegerLiteral"][0],builder)
   assert(False)

def emit_primary(p,builder):
   global context
   if "Literal" in p:
      return emit_literal(p["Literal"][0],builder)
   if "QualifiedIdentifier" in p:
      var = p["QualifiedIdentifier"][0]
      return builder.load(context[var])

   assert(False)

def emit_unary_expression(ue,builder):
   if "Primary" in ue:
      return emit_primary(ue["Primary"][0],builder)
   assert(False)

def emit_multiplicative_expression(me,builder):
   a = emit_unary_expression(me["UnaryExpression"][0],builder)
   if "StarDivModUnaryExpression" in me:
      for e in me["StarDivModUnaryExpression"]:
         b = emit_unary_expression(e["UnaryExpression"][0],builder)
         if "STAR" in e:
            a = builder.mul(a,b)
         elif "DIV" in e:
            a = builder.sdiv(a,b)
         elif "MOD" in e:
            a = builder.srem(a,b)

   return a

def emit_additive_expression(ae,builder):
   a = emit_multiplicative_expression(ae["MultiplicativeExpression"][0],builder)
   if "PlusOrMinusMultiplicativeExpression" in ae:
      for e in ae["PlusOrMinusMultiplicativeExpression"]:
         b = emit_multiplicative_expression(e["MultiplicativeExpression"][0],builder)
         if "PLUS" in e:
            a = builder.add(a,b)
         else:
            a = builder.sub(a,b)
   return a

def emit_shift_expression(se,builder):
   a = emit_additive_expression(se["AdditiveExpression"][0],builder)
   if "ShiftAdditiveExpression" in se:
     for e in se["ShiftAdditiveExpression"]:
       b = emit_additive_expression(e["AdditiveExpression"][0],builder)
       if "SR" in e:
          a = builder.ashr(a,b)
       elif "BSR" in e:
          a = builder.lshr(a,b)
       elif "SL" in e:
          a = builder.shl(a,b)
   return a

def emit_relational_expression(re,builder):
   if "RelationalShiftExpression" in re:
      assert(False)
   if "ReferenceType" in re:
      assert(False)
   if "ShiftExpression" in re:
      return emit_shift_expression(re["ShiftExpression"][0],builder)
   assert(False)

def emit_equality_expression(ee,builder):
   if "EqualityRelationalExpression" in ee:
       assert(False)
   if "RelationalExpression" in ee:
       return emit_relational_expression(ee["RelationalExpression"][0],builder)
   assert(False)

def emit_and_expression(ae,builder):
   a = emit_equality_expression(ae["EqualityExpression"][0],builder)
   if "AndEqualityExpression" in ae:
      for e in ae["AndEqualityExpression"]:
         b = emit_equality_expression(e["EqualityExpression"][0],builder)
         a = builder.and_(a,b)
   return a

def emit_exlusive_or_expression(ee,builder):
   a = emit_and_expression(ee["AndExpression"][0],builder)
   if "HatAndExpression" in ee:
     for e in ee["HatAndExpression"]:
        b = emit_and_expression(e["AndExpression"][0],builder)
        a = builder.xor(a,b)      
   return a

def emit_inclusive_or_expression(ie,builder):
   a = emit_exlusive_or_expression(ie["ExclusiveOrExpression"][0],builder)
   if "OrExclusiveOrExpression" in ie:
      for e in ie["OrExclusiveOrExpression"]:
        b = emit_exlusive_or_expression(e["ExclusiveOrExpression"][0],builder)
        a = builder.or_(a,b)      
   return a

def emit_conditional_and_expression(ce,builder):
   if "AndAndInclusiveOrExpression" in ce:
       assert(False)
   if "InclusiveOrExpression" in ce:
       return emit_inclusive_or_expression(ce["InclusiveOrExpression"][0],builder)
   assert(False)


def emit_condition_or_expression(ce, builder):
   if "OrOrConditionalAndExpression" in ce:
      assert(False)
   if "ConditionalAndExpression" in ce:
      return emit_conditional_and_expression(ce["ConditionalAndExpression"][0],builder)
   assert(False)


def emit_conditional_expression(ce,builder):
   if "QueryConditionalOrExpression" in ce:
      assert(False)
   if "ConditionalOrExpression" in ce:
      return emit_condition_or_expression(ce["ConditionalOrExpression"][0],builder)
   assert(False)

def emit_expression(se, builder):
   global context
   v = None
   if "ConditionalExpression" in se:
      v = emit_conditional_expression(se["ConditionalExpression"][0],builder)
   if "LeftHandSide" in se:
      var = se["LeftHandSide"][0]["QualifiedIdentifier"][0]
      builder.store(v,context[var])
   assert v!=None
   return v

def emit_return(r,builder):
   builder.ret(emit_expression(r,builder))

def emit_statement(s,builder):
   if "StatementExpression" in s:
      return emit_expression(s["StatementExpression"][0],builder)
   if "RETURN" in s:
      return emit_return(s["Expression"][0],builder)
   assert(False)

context = {}

def emit_local_decl(lv,builder):
   global context
   context[lv["Identifier"][0]] = builder.alloca(ir.IntType(32))

   if "VariableInitializer" in lv:
      builder.store(emit_expression(lv["VariableInitializer"][0]["Expression"][0],builder),context[lv["Identifier"][0]])


def emit_local_variable_decl(lv,builder):
   return emit_local_decl(lv["VariableDeclarators"][0]["VariableDeclarator"][0],builder)

def emit_blockstatement(bs,builder):
   if "Statement" in bs:
     return emit_statement(bs["Statement"][0],builder)
   if "LocalVariableDeclarationStatement" in bs:
     return emit_local_variable_decl(bs["LocalVariableDeclarationStatement"][0],builder)
   assert(False)


def emit_method(method,module):
   name = method["Identifier"][0]
   typo = ir.FunctionType(ir.IntType(32), (), False)
   func = ir.Function(module, typo, name)
   block = func.append_basic_block('entry')
   builder = ir.IRBuilder(block)

   methodbody = method["MethodBody"][0]
   for bs in methodbody["BlockStatements"][0]["BlockStatement"]:
      emit_blockstatement(bs,builder)


def emit_member(member,module):
   if "MethodDeclarator" in member:
      emit_method(member["MethodDeclarator"][0],module)

def emit_class(cls,module):
   body = cls["ClassBody"][0]
   decls = body["ClassBodyDeclaration"]
   for decl in decls:
      emit_member(decl["MemberDecl"][0],module)

def emit_module(unit):
   module = ir.Module(name="main")
   module.triple = binding.get_default_triple()

   for t in unit["TypeDeclaration"]:
      assert "ClassDeclaration" in t
      emit_class(t["ClassDeclaration"][0],module)

   print str(module)

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

    for rule in rules:
        execute_rule(parse_tree,rule)

    #pretty_print(parse_tree)
    json
    '''Second pass, lowering'''

    '''Third pass, emit'''
    emit_module(parse_tree["CompilationUnit"][0])

main()

