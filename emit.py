# -*- coding: utf-8 -*-
import os
import codecs
import json
from collections import OrderedDict
from llvmlite import ir
from llvmlite import binding
from signed import SIntType, Builder

def emit_integer_literal(il,builder): 
   if "DecimalNumeral" in il:
      val = int(il["DecimalNumeral"][0])
   else:
      val = int(il["HexNumeral"][0],16)


   #TODO: try to infer signed constants
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
   if "false" in l:
       return ir.Constant(ir.IntType(1), 0)
   if "true" in l:
       return ir.Constant(ir.IntType(1), 1)
   assert(False)

def is_pointer(var):
   return len(str(var.type).split("*")) > 1

def emit_primary(p,builder):
   global context
   global funcs
   if "Literal" in p:
      return emit_literal(p["Literal"][0],builder)
   if "QualifiedIdentifier" in p:
      var = p["QualifiedIdentifier"][0]
      if "IdentifierSuffix" in p:
         suf = p["IdentifierSuffix"][0]
         if "Arguments" in suf:
           a = suf["Arguments"][0]
           args = []
           func = funcs[var]["func"]
           if "Expression" in a:
              for i in range(len(a["Expression"])):
                 e = a["Expression"][i]
                 t = func.args[i]
                 e = emit_expression(e,builder)
                 e,foo,signed = auto_cast(e,t,builder,single=True,force_sign=str(t)[0])
                 args.append(e)
           return builder.call(func,args)
      else:
         if is_pointer(context[var]):
            return builder.load(context[var])
         return context[var]
   if "ParExpression" in p:
      v= emit_expression(p["ParExpression"][0]["Expression"][0],builder)
      return v
   assert(False)

def emit_unary_expression(ue,builder):
   global context
   if "Primary" in ue:
      a = emit_primary(ue["Primary"][0],builder)
   if "PostfixOp" in ue:
      for e in ue["PostfixOp"]:
         for k,v in context.items():
           if v == a.operands[0]:
              t = builder.load(v)
              if "INC" in e:
                 s = builder.add(t,ir.Constant(t.type,1))
              else:
                 s = builder.sub(t,ir.Constant(t.type,1))
              builder.store(s,v)
              found = True
              break
         assert(found)
   return a

def emit_multiplicative_expression(me,builder):
   a = emit_unary_expression(me["UnaryExpression"][0],builder)
   if "StarDivModUnaryExpression" in me:
      for e in me["StarDivModUnaryExpression"]:
         b = emit_unary_expression(e["UnaryExpression"][0],builder) 
         a,b,signed = auto_cast(a,b,builder,i=32)
         if "STAR" in e:
            a = builder.mul(a,b)
         elif "DIV" in e:
            if signed:
               a = builder.sdiv(a,b)
            else:
               a = builder.udiv(a,b)
         elif "MOD" in e:
            if signed:
               a = builder.srem(a,b)
            else:
               a = builder.urem(a,b)

   return a

def emit_additive_expression(ae,builder):
   a = emit_multiplicative_expression(ae["MultiplicativeExpression"][0],builder)
   if "PlusOrMinusMultiplicativeExpression" in ae:
      for e in ae["PlusOrMinusMultiplicativeExpression"]:
         b = emit_multiplicative_expression(e["MultiplicativeExpression"][0],builder)
         a,b,signed = auto_cast(a,b,builder,i=32)
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
       a,b,signed = auto_cast(a,b,builder,i=32)
       if "SR" in e:
          if signed:
             a = builder.ashr(a,b)
          else:
             a = builder.lshr(a,b)
       elif "BSR" in e:
          a = builder.lshr(a,b)
       elif "SL" in e:
          a = builder.shl(a,b)
   return a

def emit_relational_expression(re,builder):
   if "ReferenceType" in re:
      assert(False)

   if "ShiftExpression" in re:
      a = emit_shift_expression(re["ShiftExpression"][0],builder)

   if "RelationalShiftExpression" in re:
      for e in re["RelationalShiftExpression"]:
         b = emit_shift_expression(e["ShiftExpression"][0],builder)
         if "LT" in e:
           op = "<"
         if "LE" in e:
           ope = "<="
         if "GT" in e:
           op = ">"
         if "GE" in e:
           op = ">="	
         a = builder.icmp_signed(op,a,b)
   return a

def emit_equality_expression(ee,builder):
   if "RelationalExpression" in ee:
       a = emit_relational_expression(ee["RelationalExpression"][0],builder)

   if "EqualityRelationalExpression" in ee:
      for e in ee["EqualityRelationalExpression"]:
         b = emit_relational_expression(e["RelationalExpression"][0],builder)
         if "EQUAL" in e:
           op = "=="
         if "NOTEQUAL" in e:
           op = "!="
         a = builder.icmp_signed(op,a,b)
   return a
def emit_and_expression(ae,builder):
   a = emit_equality_expression(ae["EqualityExpression"][0],builder)
   if "AndEqualityExpression" in ae:
      for e in ae["AndEqualityExpression"]:
         b = emit_equality_expression(e["EqualityExpression"][0],builder)
         a,b,signed = auto_cast(a,b,builder,i=32)
         a = builder.and_(a,b)
   return a

def emit_exlusive_or_expression(ee,builder):
   a = emit_and_expression(ee["AndExpression"][0],builder)
   if "HatAndExpression" in ee:
     for e in ee["HatAndExpression"]:
        b = emit_and_expression(e["AndExpression"][0],builder)
        a,b,signed = auto_cast(a,b,builder,i=32)
        a = builder.xor(a,b)      
   return a

def emit_inclusive_or_expression(ie,builder):
   a = emit_exlusive_or_expression(ie["ExclusiveOrExpression"][0],builder)
   if "OrExclusiveOrExpression" in ie:
      for e in ie["OrExclusiveOrExpression"]:
        b = emit_exlusive_or_expression(e["ExclusiveOrExpression"][0],builder)
        a,b,signed = auto_cast(a,b,builder,i=32)
        a = builder.or_(a,b)      
   return a

def emit_conditional_and_expression(ce,builder):
   if "InclusiveOrExpression" in ce:
      a = emit_inclusive_or_expression(ce["InclusiveOrExpression"][0],builder)
   if "AndAndInclusiveOrExpression" in ce:
      for e in ce["AndAndInclusiveOrExpression"]:
         b = emit_inclusive_or_expression(e["InclusiveOrExpression"][0],builder)
         a = builder.and_(a,b)
   return a


def emit_condition_or_expression(ce, builder):
   if "ConditionalAndExpression" in ce:
      a = emit_conditional_and_expression(ce["ConditionalAndExpression"][0],builder)
   if "OrOrConditionalAndExpression" in ce:
      for e in ce["OrOrConditionalAndExpression"]:
         b = emit_conditional_and_expression(e["ConditionalAndExpression"][0],builder)
         a = builder.or_(a,b)
   return a


def emit_conditional_expression(ce,builder):
   if "ConditionalOrExpression" in ce:
      a = emit_condition_or_expression(ce["ConditionalOrExpression"][0],builder)
   if "QueryConditionalOrExpression" in ce:
      for e in ce["QueryConditionalOrExpression"]:
         ex = emit_expression(e["Expression"][0],builder)
         ne = emit_conditional_expression(e,builder)
         ex,ne,signed = auto_cast(ex,ne,builder)
         a = builder.select(a,ex,ne)
   return a

def emit_expression(se, builder):
   global context
   v = None
   if "ConditionalExpression" in se:
      v = emit_conditional_expression(se["ConditionalExpression"][0],builder)
   if "LeftHandSide" in se:
      for i in range(len(se["LeftHandSide"])):
         var = se["LeftHandSide"][i]["QualifiedIdentifier"][0]
         op = se["AssignmentOperator"][i]
         if "EQU" in op:
            store(v,context[var],builder)
            continue
         cv = builder.load(context[var])
         v,cv,signed = auto_cast(v,cv,builder)
         if "PLUSEQU" in op:
            v = builder.add(cv,v)    
         elif "MINUSEQU" in op:
            v = builder.sub(cv,v)
         elif "STAREQU" in op:
            v = builder.mul(cv,v)
         elif "DIVEQU" in op:
            v = builder.sdiv(cv,v)
         elif "MODEQU" in op:
            v = builder.srem(cv,v)
         elif "OREQU" in op:
            v = builder.or_(cv,v)
         elif "ANDEQU" in op:
            v = builder.and_(cv,v)
         elif "SLEQU" in op:
            v = builder.shl(cv,v)
         elif "SREQU" in op:
            if signed:
               v = builder.ashr(cv,v)   
            else:
               v = builder.lshr(cv,v)    
         elif "BSREQU" in op:
            v = builder.lshr(cv,v)    
         elif "HATEQU" in op:
            v = builder.xor(cv,v)    
         else:
            assert(False)

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

def auto_cast(a,b,builder,i=None,single=False,force_sign=None):
   asigned = False
   if "i" in str(a.type):
     at = int(str(a.type).split("i")[1])
   else:
     at = int(str(a.type).split("s")[1])
     asigned = True

   bsigned = False
   if "i" in str(b.type):
     bt = int(str(b.type).split("i")[1])
   else:
     bt = int(str(b.type).split("s")[1])
     bsigned = True
   
   if force_sign=="i" or (asigned and not bsigned):
     a = builder.tounsigned(a)

   if single==False and (force_sign=="i" or (bsigned and not asigned)):
     b = builder.tounsigned(b)

   if force_sign=="s":
     a = builder.tosigned(a)
     if single==False:
        b = builder.tosigned(b)

   if at == 1 or bt == 1:
      assert(at == bt)
      return (a,b,False) #no auto cast to integer on boolean

   signed = (asigned and bsigned and force_sign != "i") or force_sign == "s"
   if signed:
      tfunc = SIntType
      efunc = builder.sext
   else:
      tfunc = ir.IntType
      efunc = builder.zext

   if at < bt and (i != None or i < bt):
     a = efunc(a,tfunc(bt))
   elif at < i  and i != None:
     a = efunc(a,tfunc(i))
   
   if single==False:
     if bt < at and (i != None or i < at):
       b = efunc(b,tfunc(at))
     elif bt < i  and i != None:
       b = efunc(b,tfunc(i))

   return (a,b,signed)


def store(val,var,builder):
   valsigned = False
   if "i" in str(val.type):
      valt = int(str(val.type).split("i")[1])
   else:
      valt = int(str(val.type).split("s")[1])
      valsigned = True

   varsigned = False
   if "i" in str(var.type):
      vart = int(str(var.type).split("*")[0].split("i")[1])
   else:
      vart = int(str(var.type).split("*")[0].split("s")[1])
      varsigned = True

   assert(valt <= vart)

   if varsigned and not valsigned:
      val = builder.tosigned(val)

   if varsigned:
      t = SIntType(vart)
   else:
      t = ir.IntType(vart)

   if valt != vart:
      if varsigned:
        val = builder.sext(val,t)
      else:
        val = builder.zext(val,t)

   builder.store(val,var)


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
     return SIntType(32)
   if "uint" in t["BasicType"][0]:
     return ir.IntType(32)
   if "long" in t["BasicType"][0]:
     return SIntType(64)
   if "ulong" in t["BasicType"][0]:
     return ir.IntType(64)
   if "short" in t["BasicType"][0]:
     return SIntType(16)
   if "ushort" in t["BasicType"][0]:
     return ir.IntType(16)
   if "char" in t["BasicType"][0]:
     return SIntType(8)
   if "uchar" in t["BasicType"][0]:
     return ir.IntType(8)
   if "float" in t["BasicType"][0]:
     return ir.FloatType(32)
   if "double" in t["BasicType"][0]:
     return ir.FloatType(64)
   if "boolean" in t["BasicType"][0]:
     return ir.IntType(1)


def emit_local_variable_decl(lv,builder):
   t = get_type(lv["Type"][0])
   return emit_local_decl(t,lv["VariableDeclarators"][0]["VariableDeclarator"][0],builder)

def emit_blockstatement(bs,builder):
   if "Statement" in bs:
     return emit_statement(bs["Statement"][0],builder)
   if "LocalVariableDeclarationStatement" in bs:
     return emit_local_variable_decl(bs["LocalVariableDeclarationStatement"][0],builder)
   assert(False)

funcs = {}
def emit_method(method,module,decl_only):
   global funcs
   global context
   name = method["Identifier"][0]

   if decl_only:
      fps = method["FormalParameters"][0]
      types = []
      names = []
      if "FormalParameterList" in fps:
        for fp in fps["FormalParameterList"]:
           fp = fp["FormalParameter"][0]
           t = get_type(fp["Type"][0])
           types.append(t)
           names.append(fp["VariableDeclaratorId"][0]["Identifier"][0])

      typo = ir.FunctionType(ir.IntType(32), types, False)
      func = ir.Function(module, typo, name)
      func.attributes.add("noinline")
      funcs[name] = {"func" : func, "names" : names}
      return

   func = funcs[name]["func"]
   context = {}
   for i in range(len(func.args)):
     arg = func.args[i]
     name = funcs[name]["names"][i]
     context[name] = arg

   block = func.append_basic_block('entry')
   builder = Builder(block)

   methodbody = method["MethodBody"][0]
   for bs in methodbody["BlockStatements"][0]["BlockStatement"]:
      emit_blockstatement(bs,builder)


def emit_member(member,module,decl_only):
   if "MethodDeclarator" in member:
      emit_method(member["MethodDeclarator"][0],module,decl_only)

def emit_class(cls,module,decl_only):
   body = cls["ClassBody"][0]
   decls = body["ClassBodyDeclaration"]
   for decl in decls:
      emit_member(decl["MemberDecl"][0],module,decl_only)

module = None
def emit_module(unit,decl_only):
   global module
   if module == None:
      module = ir.Module(name="main")
      module.triple = binding.get_default_triple()

   for t in unit["TypeDeclaration"]:
      assert "ClassDeclaration" in t
      emit_class(t["ClassDeclaration"][0],module,decl_only)

   if not decl_only:
      print str(module).replace("s32","i32").replace("s16","i16").replace("s64","i64").replace("s8","i8")

