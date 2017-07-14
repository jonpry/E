# -*- coding: utf-8 -*-
import os
import codecs
import json
from collections import OrderedDict
from llvmlite import ir
from llvmlite import binding
from signed import SIntType, Builder
import context

def emit_float_literal(fl,builder):
   dat = fl["DecimalFloat"][0]
   #print json.dumps(dat)
   i = "0"
   frac = "0"
   if dat.keys()[0] == "DOT":
      frac = dat["Digits"][0]
   else:
      i = dat["Digits"][0]
      if len(dat["Digits"]) > 1:
         frac = dat["Digits"][1]

   st = i + "." + frac

   double = False
   if "RegExMatch" in dat:
      m = dat["RegExMatch"][0]
      if m.lower() == "d":
         double = True

   if double:
      return ir.Constant(ir.DoubleType(), float(st))   
   return ir.Constant(ir.FloatType(), float(st))   

def emit_integer_literal(il,builder): 
   if "DecimalNumeral" in il:
      val = int(il["DecimalNumeral"][0])
   else:
      val = int(il["HexNumeral"][0],16)

   signed = True
   if "SignSuffix" in il:
      signed = False
         

   #try to infer signed constants
   twidge = 0
   if signed:
      twidge = 1

   sz = 8
   if val >= (1<<(8-twidge)):
     sz = 16
   if val >= (1<<(16-twidge)):
     sz = 32
   if val >= (1<<(32-twidge)):
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
   if signed:
      return ir.Constant(SIntType(sz), val)
   return ir.Constant(ir.IntType(sz), val)

def emit_literal(l,builder):
   if "IntegerLiteral" in l:
       return emit_integer_literal(l["IntegerLiteral"][0],builder)
   if "false" in l:
       return ir.Constant(ir.IntType(1), 0)
   if "true" in l:
       return ir.Constant(ir.IntType(1), 1)
   if "FloatLiteral" in l:
       return emit_float_literal(l["FloatLiteral"][0],builder)
   assert(False)

def is_pointer(var):
   return len(str(var.type).split("*")) > 1

def emit_primary(p,builder):
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
                 e,foo,signed,flo = auto_cast(e,t,builder,single=True,force_sign=str(t)[0])
                 args.append(e)
           return builder.call(func,args)
      else:
         if is_pointer(context.get(var)):
            return builder.load(context.get(var))
         return context.get(var)
   if "ParExpression" in p:
      v= emit_expression(p["ParExpression"][0]["Expression"][0],builder)
      return v
   assert(False)

def emit_unary_expression(ue,builder):
   if "Primary" in ue:
      a = emit_primary(ue["Primary"][0],builder)
   if "PrefixOp" in ue:
      po = ue["PrefixOp"][0]
      a = emit_unary_expression(ue["UnaryExpression"][0],builder)
      if "TILDA" in po:
         a = builder.not_(a)
      elif "MINUS" in po:
         if "float" in str(a.type) or "double" in str(a.type):
            a = builder.fsub(ir.Constant(a.type,0),a)
         else:
            a = builder.neg(a)
      else:
         print json.dumps(po)
         assert(False)
   if "Type" in ue:
      t = get_type(ue["Type"][0])
      a = emit_unary_expression(ue["UnaryExpression"][0],builder)
      a = explicit_cast(a,t,builder)

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
         a,b,signed,flo = auto_cast(a,b,builder,i=32)
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
         a,b,signed,flo = auto_cast(a,b,builder,i=32)
         if "PLUS" in e:
            if flo:
              a = builder.fadd(a,b)
            else:
              a = builder.add(a,b)
         else:
            if flo:
               a = builder.fsub(a,b)
            else:
               a = builder.sub(a,b)
   return a

def emit_shift_expression(se,builder):
   a = emit_additive_expression(se["AdditiveExpression"][0],builder)
   if "ShiftAdditiveExpression" in se:
     for e in se["ShiftAdditiveExpression"]:
       b = emit_additive_expression(e["AdditiveExpression"][0],builder)
       a,b,signed,flo = auto_cast(a,b,builder,i=32)
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
         a,b,signed,flo = auto_cast(a,b,builder,i=32)
         if flo:
            a = builder.fcmp_ordered(op,a,b)
         elif signed:
            a = builder.icmp_signed(op,a,b)
         else:
            a = builder.icmp_unsigned(op,a,b)
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
         a,b,signed,flo = auto_cast(a,b,builder,i=32)
         if flo:
            a = builder.fcmp_ordered(op,a,b)
         elif signed:
            a = builder.icmp_signed(op,a,b)
         else:
            a = builder.icmp_unsigned(op,a,b)
   return a

def emit_and_expression(ae,builder):
   a = emit_equality_expression(ae["EqualityExpression"][0],builder)
   if "AndEqualityExpression" in ae:
      for e in ae["AndEqualityExpression"]:
         b = emit_equality_expression(e["EqualityExpression"][0],builder)
         a,b,signed,flo = auto_cast(a,b,builder,i=32)
         assert(not flo)
         a = builder.and_(a,b)
   return a

def emit_exlusive_or_expression(ee,builder):
   a = emit_and_expression(ee["AndExpression"][0],builder)
   if "HatAndExpression" in ee:
     for e in ee["HatAndExpression"]:
        b = emit_and_expression(e["AndExpression"][0],builder)
        a,b,signed,flo = auto_cast(a,b,builder,i=32)
        assert(not flo)
        a = builder.xor(a,b)      
   return a

def emit_inclusive_or_expression(ie,builder):
   a = emit_exlusive_or_expression(ie["ExclusiveOrExpression"][0],builder)
   if "OrExclusiveOrExpression" in ie:
      for e in ie["OrExclusiveOrExpression"]:
        b = emit_exlusive_or_expression(e["ExclusiveOrExpression"][0],builder)
        a,b,signed,flo = auto_cast(a,b,builder,i=32)
        assert(not flo)
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
         ex,ne,signed,flo = auto_cast(ex,ne,builder)
         a = builder.select(explicit_cast(a,ir.IntType(1),builder),ex,ne)
   return a

def emit_expression(se, builder):
   v = None
   if "ConditionalExpression" in se:
      v = emit_conditional_expression(se["ConditionalExpression"][0],builder)
   if "LeftHandSide" in se:
      for i in range(len(se["LeftHandSide"])):
         var = se["LeftHandSide"][i]["QualifiedIdentifier"][0]
         op = se["AssignmentOperator"][i]
         if "EQU" in op:
            store(v,context.get(var),builder)
            continue
         cv = builder.load(context.get(var))
         v,cv,signed,flo = auto_cast(v,cv,builder)
         if "PLUSEQU" in op:
            if flo:
               v = builder.fadd(cv,v)    
            else:
               v = builder.add(cv,v)    
         elif "MINUSEQU" in op:
            if flo:
               v = builder.fsub(cv,v)    
            else:
               v = builder.sub(cv,v)    
         elif "STAREQU" in op:
            if flo:
               v = builder.fmul(cv,v)    
            else:
               v = builder.mul(cv,v)    
         elif "DIVEQU" in op:
            if flo:
               v = builder.fdiv(cv,v)
            elif signed:
               v = builder.sdiv(cv,v)
            else:
               v = builder.udiv(cv,v)
         elif "MODEQU" in op:
            if flo:
               v = builder.frem(cv,v)
            elif signed:
               v = builder.srem(cv,v)
            else:
               v = builder.urem(cv,v)
         elif "OREQU" in op:
            assert(not flo)
            v = builder.or_(cv,v)
         elif "ANDEQU" in op:
            assert(not flo)
            v = builder.and_(cv,v)
         elif "SLEQU" in op:
            assert(not flo)
            v = builder.shl(cv,v)
         elif "SREQU" in op:
            assert(not flo)
            if signed:
               v = builder.ashr(cv,v)   
            else:
               v = builder.lshr(cv,v)    
         elif "BSREQU" in op:
            assert(not flo)
            v = builder.lshr(cv,v)    
         elif "HATEQU" in op:
            assert(not flo)
            v = builder.xor(cv,v)    
         else:
            assert(False)

         store(v,context.get(var),builder)


   assert v!=None
   return v

def emit_return(r,builder):
   builder.ret(emit_expression(r,builder))

def emit_par_expression(pe,builder):
   return emit_expression(pe["Expression"][0],builder)

def emit_for_init(fi,builder):
   if "StatementExpression" in fi:
      emit_expression(fi["StatementExpression"][0],builder)

def emit_for_update(fu,builder):
   if "StatementExpression" in fu:
      emit_expression(fu["StatementExpression"][0],builder)
  
def emit_statement(s,builder):
   if "StatementExpression" in s:
      return emit_expression(s["StatementExpression"][0],builder)
   if "RETURN" in s:
      return emit_return(s["Expression"][0],builder)
   if "Block" in s:
       context.push(False)
       block = s["Block"][0]
       for bs in block["BlockStatements"][0]["BlockStatement"]:
          emit_blockstatement(bs,builder)
       context.pop()
       return
   if "FOR" in s:
       context.push(False)
       emit_for_init(s["ForInit"][0],builder)
       new_block = builder.append_basic_block()
       builder.branch(new_block)
       builder.position_at_end(new_block)

       cond = emit_expression(s["Expression"][0],builder)
       cond = explicit_cast(cond,ir.IntType(1),builder)
       st_then = s["Statement"][0]

       true_block = builder.append_basic_block()
       end_block = builder.append_basic_block()
 
       builder.cbranch(cond,true_block,end_block)
       builder.position_at_end(true_block)

       #for loop contents
       context.push_break(end_block)

       emit_statement(st_then,builder)
       emit_for_update(s["ForUpdate"][0],builder)
       builder.branch(new_block)

       context.pop_break()
       builder.position_at_end(end_block)
       context.pop() 
       return
   if "IF" in s:
       c = emit_par_expression(s["ParExpression"][0],builder)
       c = explicit_cast(c,ir.IntType(1),builder)
       st_then = s["Statement"][0]

       if len(s["Statement"]) > 1:
          st_otherwise = s["Statement"][1]

          with builder.if_else(c) as (then, otherwise):
             with then:
                emit_statement(st_then,builder)
             with otherwise:
                emit_statement(st_otherwise,builder)
       else:
          with builder.if_then(c) as then:
             emit_statement(st_then,builder)

       #print json.dumps(st)
       return
   if "BREAK" in s:
       builder.branch(context.get_break())
       return 

   print json.dumps(s)
   assert(False)

def type_info(a):
   signed = False
   flo = False
   if "i" in str(a):
     t = int(str(a).split("i")[1])
   elif "s" in str(a):
     t = int(str(a).split("s")[1])
     signed = True
   elif "float" in str(a):
     t = 32
     flo = True
   elif "double" in str(a):
     t = 64
     flo = True
   return (signed,flo,t)

def auto_cast(a,b,builder,i=None,single=False,force_sign=None):
   asigned, afloat, at = type_info(a.type)
   bsigned, bfloat, bt = type_info(b.type)

   if at == 1 or bt == 1:
      assert(at == bt)
      return (a,b,False,False) #no auto cast to integer on boolean

   #TODO, this is all wrong need doubles for 64bit ints or other doubles
   if afloat or bfloat:
      if not afloat:
        if asigned:
          if at > 32:
             a = builder.sitofp(a,ir.DoubleType())
          else:
             a = builder.sitofp(a,ir.FloatType())
        else:
          if at > 32:
             a = builder.uitofp(a,ir.DoubleType())
          else:
             a = builder.uitofp(a,ir.FloatType())
      elif not bfloat:
        if bsigned:
          if bt > 32:
             b = builder.sitofp(b,ir.DoubleType())
          else:
             b = builder.sitofp(b,ir.FloatType())
        else:
          if bt > 32:
             b = builder.uitofp(b,ir.DoubleType())
          else:
             b = builder.uitofp(b,ir.FloatType())
      else: #both are floats
        if at > bt:
           b = builder.fpext(b,ir.DoubleType())
        elif at < bt:
           a = builder.fpext(a,ir.DoubleType())
      return (a,b,False,True)

   if force_sign=="i" or (asigned and not bsigned):
     a = builder.tounsigned(a)

   if single==False and (force_sign=="i" or (bsigned and not asigned)):
     b = builder.tounsigned(b)

   if force_sign=="s":
     a = builder.tosigned(a)
     if single==False:
        b = builder.tosigned(b)

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

   return (a,b,signed,False)

def explicit_cast(a,t,builder):
   asigned, afloat, at = type_info(a.type)
   tsigned, tfloat, tt = type_info(t)

   if tt == 1:
      if at == 1:
         return a

      if afloat:
         return builder.fcmp_unordered("!=",a,ir.Constant(ir.FloatType(),0))
      return builder.icmp_unsigned("!=",a,ir.Constant(a.type,0))

   if tfloat:
      if afloat:
         return a
      if asigned:
         return builder.sitofp(a,ir.FloatType())
      return builder.uitofp(a,ir.FloatType())

   if tt < at:
      return builder.trunc(a,t)

   if tt > at:
      if asigned:
         return builder.sext(a,t)
      return builder.zext(a,t)

   if tsigned:
      if afloat:
         return builder.fptosi(a,t)
      else:
         return builder.tosigned(a)
   if afloat:
      return builder.fptoui(a,t)
   return builder.tounsigned(a)


def store(val,var,builder):
   valsigned = False
   valfloat = False
   if "i" in str(val.type):
      valt = int(str(val.type).split("i")[1])
   elif "s" in str(val.type):
      valt = int(str(val.type).split("s")[1])
      valsigned = True
   elif "float" in str(val.type):
      valt = 32
      varfloat = True
   elif "double" in str(val.type):
      valt = 64
      varfloat = True

   varsigned = False
   varfloat = False
   if "i" in str(var.type):
      vart = int(str(var.type).split("*")[0].split("i")[1])
   elif "s" in str(var.type):
      vart = int(str(var.type).split("*")[0].split("s")[1])
      varsigned = True
   elif "float" in str(var.type):
      vart = 32
      varfloat = True
   elif "double" in str(var.type):
      vart = 64
      varfloat = True

   if varsigned and not valsigned:
      val = builder.tosigned(val)

   if varsigned:
      t = SIntType(vart)
   elif varfloat:
      if vart == 32:
         t = ir.FloatType()
      else:
         t = ir.DoubleType()
   else:
      t = ir.IntType(vart)

   if varfloat and not valfloat:
      if valsigned:
         val = builder.sitofp(val,t)
      else:
         val = builder.uitofp(val,t)

   if varfloat:
      if valt != vart:
         val = builder.fpext(val,t)
   else:
      if valt != vart:
         if valsigned:
           val = builder.sext(val,t)
         else:
           val = builder.zext(val,t)
   
   builder.store(val,var)

static_ctors = []
def emit_member_decl(t,static,st,module,pas):
   global static_ctors
   ident = st["Identifier"][0]
   if pas == "decl_only":
      if static:
         data = ir.GlobalVariable(module,t,ident)
         data.initializer = ir.Constant(t,0)
         context.create_global(ident,data)
         return data
      else:
         context.create_member(t,ident)

   if pas == "method_body":
      if static:
         typo = ir.FunctionType(ir.VoidType(), [], False)
      else:
         typo = ir.FunctionType(ir.VoidType(), [context.get_type().as_pointer()], False)

      func = ir.Function(module, typo, "init." + ident)
      func.attributes.add("noinline")
      block = func.append_basic_block('entry')
      builder = Builder(block)

      val = emit_expression(st["VariableInitializer"][0]["Expression"][0],builder)
      if static:
         var = context.get(ident)
      else:
         var = context.get(ident,func.args[0],builder)
      store(val,var,builder)
      builder.ret_void()
      if static:
         static_ctors.append(func)

def emit_local_decl(t,lv,builder):
   context.create(lv["Identifier"][0], builder.alloca(t))

   if "VariableInitializer" in lv:
      val = emit_expression(lv["VariableInitializer"][0]["Expression"][0],builder)
      var = context.get(lv["Identifier"][0])
      store(val,var,builder)


def get_type(t):
   assert("BasicType" in t)
   if "uint" in t["BasicType"][0]:
     return ir.IntType(32)
   if "int" in t["BasicType"][0]:
     return SIntType(32)
   if "ulong" in t["BasicType"][0]:
     return ir.IntType(64)
   if "long" in t["BasicType"][0]:
     return SIntType(64)
   if "ushort" in t["BasicType"][0]:
     return ir.IntType(16)
   if "short" in t["BasicType"][0]:
     return SIntType(16)
   if "uchar" in t["BasicType"][0]:
     return ir.IntType(8)
   if "char" in t["BasicType"][0]:
     return SIntType(8)
   if "float" in t["BasicType"][0]:
     return ir.FloatType()
   if "double" in t["BasicType"][0]:
     return ir.DoubleType()
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
def emit_method(method,module,pas):
   global funcs
   name = method["Identifier"][0]

   if pas == "decl_only":
      tv = method["TypeOrVoid"][0]
      if "Type" in tv:
        rtype = get_type(tv["Type"][0])
      else:
        rtype = ir.VoidType()
      fps = method["FormalParameters"][0]
      types = []
      names = []
      if "FormalParameterList" in fps:
        for fp in fps["FormalParameterList"]:
           fp = fp["FormalParameter"][0]
           t = get_type(fp["Type"][0])
           types.append(t)
           names.append(fp["VariableDeclaratorId"][0]["Identifier"][0])

      typo = ir.FunctionType(rtype, types, False)
      func = ir.Function(module, typo, name)
      func.attributes.add("noinline")
      funcs[name] = {"func" : func, "names" : names, "ret" : rtype}
      return

   func = funcs[name]["func"]
   context.push(True)
   for i in range(len(func.args)):
     arg = func.args[i]
     context.create(funcs[name]["names"][i], arg)

   block = func.append_basic_block('entry')
   builder = Builder(block)

   methodbody = method["MethodBody"][0]
   for bs in methodbody["BlockStatements"][0]["BlockStatement"]:
      emit_blockstatement(bs,builder)

   if funcs[name]["ret"] == ir.VoidType():
      builder.ret_void()
   context.pop()

def emit_member(member,module,pas):
   static = False;
   if "Modifier" in member:
      mods = member["Modifier"]
      if "static" in mods:
         static = True;

   if "MethodDeclarator" in member:
      return emit_method(member["MethodDeclarator"][0],module,pas)
   if "VariableDeclarators" in member:
      t = get_type(member["Type"][0])
      return emit_member_decl(t,static,member["VariableDeclarators"][0]["VariableDeclarator"][0],module,pas)
   print json.dumps(member)
   assert(False)

def emit_class(cls,module,pas):
   body = cls["ClassBody"][0]
   decls = body["ClassBodyDeclaration"]
   ident = cls["Identifier"][0]
   context.push_class(ident)
   for decl in decls:
      emit_member(decl["MemberDecl"][0],module,pas)
   context.pop_class()

   if pas == "decl_only":
      context.set_type(None,ident)
      t = module.context.get_identified_type(context.fqid())
      types = context.get_member_types()
      t.set_body(*types)
      context.set_type(t,ident)

def make_bytearray(buf):
    """
    Make a byte array constant from *buf*.
    """
    b = bytearray(buf)
    n = len(b)
    return ir.Constant(ir.ArrayType(ir.IntType(8), n), b)

def global_constant(module, name, value):
    """
    Get or create a (LLVM module-)global constant with *name* or *value*.
    """
    data = ir.GlobalVariable(module,value.type,name)
    data.global_constant = True
    data.initializer = value
    return data

def emit_print_func(module,name,fmt,typo):
    global funcs
    fnty = ir.FunctionType(ir.VoidType(), [typo])
    func = ir.Function(module, fnty, name=name)
    func.attributes.add("noinline")
    block = func.append_basic_block('entry')
    builder = Builder(block)
    funcs[name] = {"func" : func, "names" : ["v"], "ret" : ir.VoidType()}
    pfn = funcs["printf"]["func"]

    #create global for string
    fmt_bytes = make_bytearray((fmt + '\n\00').encode('ascii'))
    global_fmt = global_constant(module, "print_" + name.split("_")[1] + "_format", fmt_bytes)
    global_fmt = builder.bitcast(global_fmt, ir.IntType(8).as_pointer())

    builder.call(pfn, [global_fmt, func.args[0]])
    builder.ret_void()


def emit_print_funcs(module):
    global funcs
    fnty = ir.FunctionType(ir.IntType(32), [ir.IntType(8).as_pointer()], var_arg=True)
    fn = ir.Function(module, fnty, name="printf")
    funcs["printf"] = {"func" : fn, "names" : [], "ret" : ir.IntType(32)}

    emit_print_func(module, "print_uint", "%u", ir.IntType(32))
    emit_print_func(module, "print_ulong", "%ul", ir.IntType(64))
    emit_print_func(module, "print_int", "%d", ir.IntType(32))
    emit_print_func(module, "print_long", "%dl", ir.IntType(64))
    emit_print_func(module, "print_float", "%f", ir.DoubleType())
    emit_print_func(module, "print_double", "%f", ir.DoubleType())

module = None
def emit_module(unit,pas):
   global module
   global static_ctors
   global funcs
   if module == None:
      module = ir.Module(name="main")
      module.triple = binding.get_default_triple()
      if "PackageDeclaration" in unit:
          context.set_package(unit["PackageDeclaration"][0]["QualifiedIdentifier"][0])

   if pas == "method_body":
       emit_print_funcs(module)

   for t in unit["TypeDeclaration"]:
      assert "ClassDeclaration" in t
      emit_class(t["ClassDeclaration"][0],module,pas)

   if pas == "method_body":
      typo = ir.FunctionType(ir.VoidType(), [])
      func = ir.Function(module, typo, name="main")
      func.attributes.add("noinline")
      block = func.append_basic_block('entry')
      builder = Builder(block)
      for f in static_ctors:
        builder.call(f,[])

      builder.call(funcs["main_entry"]["func"],[])

      builder.ret_void()
      print str(module).replace("s32","i32").replace("s16","i16").replace("s64","i64").replace("s8","i8")

