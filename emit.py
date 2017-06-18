# -*- coding: utf-8 -*-
import os
import codecs
import json
from collections import OrderedDict
from llvmlite import ir
from llvmlite import binding

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

