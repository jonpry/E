# -*- coding: utf-8 -*-
import os
import codecs
import json
from collections import OrderedDict
from llvmlite import ir
from llvmlite import binding

def emit_integer_literal(il,builder): 
   val = int(il["DecimalNumeral"][0])
   sz = 8
   if val > 255:
     sz = 16
   if val >= (1<<16):
     sz = 32
   if val >= (1<<32):
     sz = 64
 
   if "SizeSuffix" in il:
     suf = il["SizeSuffix"][0].lower()
     if suf == "l":
        nsz = 64
     elif suf == "i":
        nsz = 32
     elif suf == "s":
        nsz = 16
     elif suf == "b":
        nsz = 8
     assert(nsz >= sz)
     sz = nsz
   return ir.Constant(ir.IntType(sz), val)

def emit_literal(l,builder):
   if "IntegerLiteral" in l:
       return emit_integer_literal(l["IntegerLiteral"][0],builder)
   assert(False)

def emit_primary(p,builder):
   global context
   if "Literal" in p:
      print json.dumps(p)
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
         a,b = auto_cast(a,b,builder,i=32)
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
         a,b = auto_cast(a,b,builder,i=32)
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
       a,b = auto_cast(a,b,builder,i=32)
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
         a,b = auto_cast(a,b,builder,i=32)
         a = builder.and_(a,b)
   return a

def emit_exlusive_or_expression(ee,builder):
   a = emit_and_expression(ee["AndExpression"][0],builder)
   if "HatAndExpression" in ee:
     for e in ee["HatAndExpression"]:
        b = emit_and_expression(e["AndExpression"][0],builder)
        a,b = auto_cast(a,b,builder,i=32)
        a = builder.xor(a,b)      
   return a

def emit_inclusive_or_expression(ie,builder):
   a = emit_exlusive_or_expression(ie["ExclusiveOrExpression"][0],builder)
   if "OrExclusiveOrExpression" in ie:
      for e in ie["OrExclusiveOrExpression"]:
        b = emit_exlusive_or_expression(e["ExclusiveOrExpression"][0],builder)
        a,b = auto_cast(a,b,builder,i=32)
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
      store(v,context[var],builder)
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

def auto_cast(a,b,builder,i=None):
   at = int(str(a.type).split("i")[1])
   bt = int(str(b.type).split("i")[1])

   if at < bt and (i != None or i < bt):
     a = builder.sext(a,ir.IntType(bt))
   elif at < i  and i != None:
     a = builder.sext(a,ir.IntType(i))

   if bt < at and (i != None or i < at):
     b = builder.sext(b,ir.IntType(at))
   elif bt < i  and i != None:
     b = builder.sext(b,ir.IntType(i))

   return (a,b)


def store(val,var,builder):
   valt = int(str(val.type).split("i")[1])
   vart = int(str(var.type).split("*")[0].split("i")[1])

   assert(valt <= vart)

   t = ir.IntType(vart)

   v = builder.sext(val,t)
   builder.store(v,var)


def emit_local_decl(t,lv,builder):
   global context
   context[lv["Identifier"][0]] = builder.alloca(t)

   if "VariableInitializer" in lv:
      val = emit_expression(lv["VariableInitializer"][0]["Expression"][0],builder)
      var = context[lv["Identifier"][0]]
      store(val,var,builder)

def get_type(t):
   assert("BasicType" in t)
   if "int" in t["BasicType"][0]:
     return ir.IntType(32)
   if "long" in t["BasicType"][0]:
     return ir.IntType(64)
   if "short" in t["BasicType"][0]:
     return ir.IntType(16)
   if "byte" in t["BasicType"][0]:
     return ir.IntType(8)
   if "float" in t["BasicType"][0]:
     return ir.FloatType(32)
   if "double" in t["BasicType"][0]:
     return ir.FloatType(64)


def emit_local_variable_decl(lv,builder):
   t = get_type(lv["Type"][0])
   return emit_local_decl(t,lv["VariableDeclarators"][0]["VariableDeclarator"][0],builder)

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

