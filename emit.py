# -*- coding: utf-8 -*-
import os
import codecs
import json
import sys
from collections import OrderedDict
from llvmlite import ir
from llvmlite import binding
from signed import SIntType, Builder
import context, cast

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

def emit_call(tup,suf,builder):
   a = suf["Arguments"][0]
   args = []
   func = tup[0]["func"]
   static =  tup[0]["static"]
   if not static:
      assert(tup[1] != None)
      args.append(tup[1]) #todo: check caller is not static
   if "Expression" in a:
      for i in range(len(a["Expression"])):
          e = a["Expression"][i]
          t = func.args[i if static else i+1]
          e = emit_expression(e,builder)
          e,foo,signed,flo = cast.auto_cast(e,t,builder,single=True,force_sign=str(t)[0])
          args.append(e)
   return builder.call(func,args)


def emit_primary(p,builder):
   if "Literal" in p:
      return emit_literal(p["Literal"][0],builder)
   if "QualifiedIdentifier" in p:
      var = p["QualifiedIdentifier"][0]
      if "IdentifierSuffix" in p:
         suf = p["IdentifierSuffix"][0]
         if "Arguments" in suf:
           tup = context.get(var)
           return emit_call(tup,suf,builder)
      else:
         t = context.get(var,builder)
         if context.is_pointer(t):
            return builder.load(t)
         return t
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
      a = cast.explicit_cast(a,t,builder)

   if "PostfixOp" in ue:
      e = ue["PostfixOp"][0]
      ident = ue["Primary"][0]["QualifiedIdentifier"][0]
      t = context.get(ident,builder)
      ot = t
      if context.is_pointer(t):
         t = builder.load(t)
      if "INC" in e:
         s = builder.add(t,ir.Constant(t.type,1))
      else:
         s = builder.sub(t,ir.Constant(t.type,1))
      if context.is_pointer(ot):
         builder.store(s,ot)
      else:
         context.set(ident,s)
      return t
   return a

def emit_multiplicative_expression(me,builder):
   a = emit_unary_expression(me["UnaryExpression"][0],builder)
   if "StarDivModUnaryExpression" in me:
      for e in me["StarDivModUnaryExpression"]:
         b = emit_unary_expression(e["UnaryExpression"][0],builder) 
         a,b,signed,flo = cast.auto_cast(a,b,builder,i=32)
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
         a,b,signed,flo = cast.auto_cast(a,b,builder,i=32)
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
       a,b,signed,flo = cast.auto_cast(a,b,builder,i=32)
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
         a,b,signed,flo = cast.auto_cast(a,b,builder,i=32)
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
         a,b,signed,flo = cast.auto_cast(a,b,builder,i=32)
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
         a,b,signed,flo = cast.auto_cast(a,b,builder,i=32)
         assert(not flo)
         a = builder.and_(a,b)
   return a

def emit_exlusive_or_expression(ee,builder):
   a = emit_and_expression(ee["AndExpression"][0],builder)
   if "HatAndExpression" in ee:
     for e in ee["HatAndExpression"]:
        b = emit_and_expression(e["AndExpression"][0],builder)
        a,b,signed,flo = cast.auto_cast(a,b,builder,i=32)
        assert(not flo)
        a = builder.xor(a,b)      
   return a

def emit_inclusive_or_expression(ie,builder):
   a = emit_exlusive_or_expression(ie["ExclusiveOrExpression"][0],builder)
   if "OrExclusiveOrExpression" in ie:
      for e in ie["OrExclusiveOrExpression"]:
        b = emit_exlusive_or_expression(e["ExclusiveOrExpression"][0],builder)
        a,b,signed,flo = cast.auto_cast(a,b,builder,i=32)
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
         ex,ne,signed,flo = cast.auto_cast(ex,ne,builder)
         a = builder.select(cast.explicit_cast(a,ir.IntType(1),builder),ex,ne)
   return a

def emit_expression(se, builder):
   v = None
   if "ConditionalExpression" in se:
      v = emit_conditional_expression(se["ConditionalExpression"][0],builder)
   if "LeftHandSide" in se:
      for i in range(len(se["LeftHandSide"])):
         var = se["LeftHandSide"][i]["QualifiedIdentifier"][0]
         op = se["AssignmentOperator"][i]

         cv = context.get(var,builder)
         if "EQU" in op:
             if context.is_pointer(cv):
                v = cast.explicit_cast(v,cv.type.pointee,builder)
                builder.store(v,cv)
             else:
                v = cast.explicit_cast(v,cv.type,builder)
                context.set(var,v)
             return v
 
         if context.is_pointer(cv):
            cv = builder.load(cv)  

         if isinstance(cv,ir.Type):
            ct = cv
         else:
            ct = cv.type
         v,cv,signed,flo = cast.auto_cast(v,cv,builder)

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

         v = cast.explicit_cast(v,ct,builder)
         cv = context.get(var,builder)
         if context.is_pointer(cv):
            cv = builder.store(v,cv)
         else:   
            context.set(var,v)

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
  
init_ctx = {}
for_ctx = {}

def emit_statement(s,pas,builder):
   global init_ctx, for_ctx

   if "StatementExpression" in s:
      return emit_expression(s["StatementExpression"][0],builder)
   if "RETURN" in s:
      return emit_return(s["Expression"][0],builder)
   if "Block" in s:
       context.push(False)
       block = s["Block"][0]
       for bs in block["BlockStatements"][0]["BlockStatement"]:
          emit_blockstatement(bs,pas,builder)
       context.pop(builder)
       return
   if "FOR" in s or "WHILE" in s:
       do = "DO" in s
       context.push(False)
       if "ForInit" in s:
          emit_for_init(s["ForInit"][0],builder)
       init_context = context.push(False)
       init_block = builder.block

       cond_block = builder.append_basic_block('bb')
       builder.branch(cond_block)
       builder.position_at_end(cond_block)

       phis = {}
       if json.dumps(s) in for_ctx:
         for k in [k[0] for k in context.different_in(init_context,for_ctx[json.dumps(s)])]:
            phi = builder.phi(init_context[k].type)
            phi.add_incoming(init_context[k],init_block)
            context.set(k,phi)
            phis[k] = phi

       if do:
          phi = builder.phi(ir.IntType(1))
          phi.add_incoming(ir.Constant(ir.IntType(1),1),init_block)
          doreg = phi

       init_context = context.current()

       cond = emit_expression(s["Expression"][0],builder)
       cond = cast.explicit_cast(cond,ir.IntType(1),builder)

       true_block = builder.append_basic_block('bb')
       end_block = builder.append_basic_block('bb')
       update_block = builder.append_basic_block('bb')
 
       if do:
         cond = builder.or_(doreg,cond)

       builder.cbranch(cond,true_block,end_block)
       builder.position_at_end(true_block)

       #for loop contents
       context.push(False)
       breaks = []
       continues = []
       context.breaks.push((end_block,breaks))
       context.continues.push((update_block,continues))

       emit_statement(s["Statement"][0],pas,builder)
       builder.branch(update_block)
       last_block = builder.block
       builder.position_at_end(update_block)

       update_context = context.current()
       ncontinues = {}
       for c in continues:
          for k in [k[0] for k in context.different_in(update_context,c[1])]:
             if k in ncontinues:
                ncontinues[k].append(c)
             else:
                ncontinues[k] = [c]

       #print ncontinues
       #exit(0)
       for k,a in ncontinues.items():
          phi = builder.phi(update_context[k].type)
          phi.add_incoming(update_context[k],last_block)
          r = continues[:]
          for c in a:
            phi.add_incoming(c[1][k],c[0])
            if c in r:
              r.remove(c)
          for c in r:
            phi.add_incoming(c[1][k],c[0])
          context.set(k,phi)

       if "ForUpdate" in s:
          emit_for_update(s["ForUpdate"][0],builder)

       builder.branch(cond_block)
       context.breaks.pop()
       context.continues.pop()
       for_context = context.pop(builder)[0]      

       builder.position_at_end(end_block)
       #Two pops
       context.pop(builder) 
       context.pop(builder) 

       if json.dumps(s) in for_ctx:
          for k,v in phis.items():
             v.add_incoming(for_context[k],update_block)
             context.set(k,v)

          if do:
             doreg.add_incoming(ir.Constant(ir.IntType(1),0),update_block)

          nbreaks = {}
          for b in breaks:
             for k in [k[0] for k in context.different_in(init_context,b[1])]:
                if k in nbreaks:
                   nbreaks[k].append(b)
                else:
                   nbreaks[k] = [b]
          
          for k,a in nbreaks.items():
              phi = builder.phi(init_context[k].type)
              phi.add_incoming(context.get(k),cond_block)
              s = breaks[:]
              for b in a:
                phi.add_incoming(b[1][k],b[0])
                if b in s:
                   s.remove(b)
              for b in s:
                phi.add_incoming(b[1][k],b[0])                
              context.set(k,phi)
       else:
          for_ctx[json.dumps(s)] = for_context 

       return
   if "IF" in s:
       c = emit_par_expression(s["ParExpression"][0],builder)
       c = cast.explicit_cast(c,ir.IntType(1),builder)
       st_then = s["Statement"][0]

       old_context = context.push(False)
       old_block = builder.block

       true_block = builder.append_basic_block('bb')
       false_block = builder.append_basic_block('bb')
       end_block = builder.append_basic_block('bb')

       builder.cbranch(c,true_block,false_block)
       builder.position_at_end(true_block)
       emit_statement(st_then,pas,builder)
       true_context = context.pop(builder)[0]
       has_phi = True
       context.push(False,old_context)
       if not builder.block.is_terminated:
          builder.branch(end_block)
       else:
          has_phi = False
       true_block = builder.block

       builder.position_at_end(false_block)
       if len(s["Statement"]) > 1:
          st_otherwise = s["Statement"][1]
          emit_statement(st_otherwise,pas,builder)
       false_context = context.pop(builder)[0]
       false_block = builder.block
       if not builder.block.is_terminated:
          builder.branch(end_block)
       else:
          has_phi = False

       builder.position_at_end(end_block)

       then_set = [k[0] for k in context.different_in(old_context,true_context)]
       else_set = [k[0] for k in context.different_in(old_context,false_context)]
       union = then_set[:]
       if len(else_set) > 0:
          union.append(*else_set)
       union = list(set(union))
       if has_phi:
          for k in union:
             phi = builder.phi(old_context[k].type)
             if k in then_set:
                phi.add_incoming(true_context[k],true_block)
             else:
                phi.add_incoming(old_context[k],true_block)
             if k in else_set:
                phi.add_incoming(false_context[k],false_block)
             else:
                phi.add_incoming(old_context[k],false_block)
             context.set(k,phi)
       return
   if "BREAK" in s:
       builder.branch(context.breaks.get()[0])
       context.breaks.get()[1].append((builder.block,context.current()))
       return 
   if "CONTINUE" in s:
       builder.branch(context.continues.get()[0])
       context.continues.get()[1].append((builder.block,context.current()))
       return 
   print json.dumps(s)
   assert(False)

static_ctors = []
ctors = []
def emit_member_decl(t,static,st,module,pas):
   global static_init
   global init
   ident = st["Identifier"][0]
   if pas == "decl_type":
      context.classs.create_member(t,ident,static)

   if pas == "method_body" or pas == "method_phi":
      if "VariableInitializer" not in st:
          return

      if static:
         builder = static_init
      else:
         builder = init
         context.thiss.push(init.function.args[0])

      context.push(False)

      val = emit_expression(st["VariableInitializer"][0]["Expression"][0],builder)
      val = cast.explicit_cast(val,t,builder)
      var = context.get(ident,builder)
      if context.is_pointer(var):
         builder.store(val,var)
      else:       
         context.set(ident,val,builder)

      context.pop(builder)
      if not static:
         context.thiss.pop()

def emit_lifetime(var,t,action,builder):
    #sz = builder.gep(ir.Constant(t.as_pointer(),None),[ir.Constant(ir.IntType(32),1)])
    #sz = builder.ptrtoint(sz,ir.IntType(64))
    var = builder.bitcast(var,ir.IntType(8).as_pointer())
    sz = ir.Constant(ir.IntType(64),-1)
    builder.call(context.get("llvm.lifetime." + action)[0]["func"], [sz, var])


def emit_local_decl(t,lv,pas,builder):
   if isinstance(t,ir.Aggregate):
      nid = "." + builder.block.name + "." + lv["Identifier"][0]
      if pas == "method_phi":
          context.create(lv["Identifier"][0], builder.alloca(t))
          context.funcs.get(builder.function.name)["allocs"][nid] = t
      elif pas == "method_body":
          var = context.get(nid)
          context.create(lv["Identifier"][0], var)
          #lifetime management
          emit_lifetime(var,t,'start',builder)
      else:
          assert(False)
   else:
      context.create(lv["Identifier"][0], t)

   if "Arguments" in lv: #Constructor
      t = str(t).split("\"")[1]
      t += "." + t.split(".")[-1]
      func = (context.get(t)[0],context.get(lv["Identifier"][0]))
      emit_call(func,lv,builder)

   if "VariableInitializer" in lv:
      val = emit_expression(lv["VariableInitializer"][0]["Expression"][0],builder)
      var = context.get(lv["Identifier"][0],builder)
      if isinstance(var,ir.Type):
         context.set(lv["Identifier"][0], cast.explicit_cast(val,var,builder))
      else:
         context.set(lv["Identifier"][0], cast.explicit_cast(val,var.type,builder))


def get_type(t):
   if "BasicType" in t:
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
   if "ClassType" in t:
     return context.classs.get_class_type(t["ClassType"][0]["Identifier"][0])

   print json.dumps(t)
   assert(False)


def emit_local_variable_decl(lv,pas,builder):
   t = get_type(lv["Type"][0])
   l = lv["VariableDeclarators"][0]["VariableDeclarator"]
   for e in l:
      emit_local_decl(t,e,pas,builder)

def emit_blockstatement(bs,pas,builder):
   if "Statement" in bs:
     return emit_statement(bs["Statement"][0],pas,builder)
   if "LocalVariableDeclarationStatement" in bs:
     return emit_local_variable_decl(bs["LocalVariableDeclarationStatement"][0],pas,builder)
   assert(False)

def reset_func(func):
   func.blocks = []
   func.scope = ir._utils.NameScope()
   func.args = tuple([ir.Argument(func, t)
                           for t in func.ftype.args])

def emit_method(method,static,native,constructor,module,pas):
   name = method["Identifier"][0]

   if pas == "decl_type":
      return

   if pas == "decl_methods":
      rtype = ir.VoidType()

      if "TypeOrVoid" in method:
        tv = method["TypeOrVoid"][0]
        if "Type" in tv:
           rtype = get_type(tv["Type"][0])

      fps = method["FormalParameters"][0]
      types = []
      names = []

      if not static and not native:
         types.append(context.classs.get_type(module,False).as_pointer())
         names.append("this")
      
      if "FormalParameterList" in fps:
        fps = fps["FormalParameterList"][0]["FormalParameter"]
        for fp in fps:
           t = get_type(fp["Type"][0])
           types.append(t)
           names.append(fp["VariableDeclaratorId"][0]["Identifier"][0])

      native_name = name
      name = context.classs.fqid() + "." + name
      func = context.funcs.get_native(native_name)
      if not native or func == None:
         typo = ir.FunctionType(rtype, types, False)
         func = ir.Function(module, typo, native_name if native else name)
         func.attributes.add("noinline")
      context.funcs.create(name,{"func" : func, "names" : names, "ret" : rtype, "static" : (static or native), "native" : native, "allocs" : {}})
      return

   if "MethodBody" not in method:
      return

   assert(not native)

   func = context.get(name)[0]["func"]
   context.push(True)
   context.funcs.push(context.get(name))

   if not static:
       context.thiss.push(func.args[0])
   for i in range(len(func.args)):
     arg = func.args[i]
     context.create(context.get(name)[0]["names"][i], arg)
    
   reset_func(func)
   block = func.append_basic_block('bb')
   builder = Builder(block)

   if pas == "method_body":
      allocs = context.get(name)[0]["allocs"]
      for k,v in allocs.items():
          context.create(k,builder.alloca(v))

   if constructor:
       builder.call(context.classs.get_init(),[func.args[0]])

   methodbody = method["MethodBody"][0]
   for bs in methodbody["BlockStatements"][0]["BlockStatement"]:
      emit_blockstatement(bs,pas,builder)

   if not static:
      context.thiss.pop()
   context.funcs.pop()
   context.pop(builder)

   if context.get(name)[0]["ret"] == ir.VoidType():
      builder.ret_void()

def emit_member(member,module,pas):
   static = False
   native = False
   if "Modifier" in member:
      mods = member["Modifier"]
      static = "static" in mods;
      native = "native" in mods;

   if "MethodDeclarator" in member:
      return emit_method(member["MethodDeclarator"][0],static,native,False,module,pas)
   if "ConstructorDeclarator" in member:
      return emit_method(member["ConstructorDeclarator"][0],False,False,True,module,pas)

   if "VariableDeclarators" in member:
      t = get_type(member["Type"][0])
      l = member["VariableDeclarators"][0]["VariableDeclarator"]
      for e in l:
         emit_member_decl(t,static,e,module,pas)
      return
   print json.dumps(member)
   assert(False)

def emit_class(cls,module,pas):
   global init
   global static_init
   global static_ctors

   body = cls["ClassBody"][0]
   decls = body["ClassBodyDeclaration"]
   ident = cls["Identifier"][0]
   context.classs.push(ident)

   if pas == "decl_type":
      context.classs.set_type(None,None,ident)

   if pas == "decl_methods":
      typo = ir.FunctionType(ir.VoidType(), [context.classs.get_type(module,False).as_pointer()], False)
      func = ir.Function(module, typo, context.classs.fqid() + ".init")
      func.attributes.add("noinline")
      context.classs.set_init(func)

      typo = ir.FunctionType(ir.VoidType(), [], False)
      func = ir.Function(module, typo, context.classs.fqid() + ".static.init")
      func.attributes.add("noinline")
      context.classs.set_static_init(func)
      static_ctors.append(func)

   if pas == "method_body" or pas == "method_phi":
      func = context.classs.get_init()
      reset_func(func)

      block = func.append_basic_block('bb')
      init = Builder(block)

      func = context.classs.get_static_init()
      reset_func(func)
      block = func.append_basic_block('bb')
      static_init = Builder(block)

   if "EXTENDS" in cls:
      sup = context.get(cls["ClassType"][0]["Identifier"][0])
      context.classs.set_extends(sup)

   for decl in decls:
      static = "STATIC" in decl

      if "MemberDecl" in decl:
         emit_member(decl["MemberDecl"][0],module,pas)
      elif "Block" in decl:
         if pas == "method_body" or pas == "method_phi":
             builder = static_init if static else init
             context.push(False)
             if not static:
                context.thiss.push(init.function.args[0])
             block = decl["Block"][0]
             for bs in block["BlockStatements"][0]["BlockStatement"]:
                emit_blockstatement(bs,pas,builder)
             if not static:
                context.thiss.pop()
             context.pop(builder)
      else:
        assert(False)

   if pas == "method_body" or pas == "method_phi":
      init.ret_void()
      static_init.ret_void()

   context.classs.pop()

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
    func = context.funcs.get_native(name)
    if func == None:
       #assert(False)
       fnty = ir.FunctionType(ir.VoidType(), [typo])
       func = ir.Function(module, fnty, name=name)
       func.attributes.add("noinline")
       context.funcs.create(name,{"func" : func, "names" : ["v"], "ret" : ir.VoidType(), "static" : True, "native" : True, "allocs" : {}})

    block = func.append_basic_block('bb')
    builder = Builder(block)
    pfn = context.get("printf")[0]["func"]

    #create global for string
    fmt_bytes = make_bytearray((fmt + '\n\00').encode('ascii'))
    global_fmt = global_constant(module, "print_" + name.split("_")[1] + "_format", fmt_bytes)
    global_fmt = builder.bitcast(global_fmt, ir.IntType(8).as_pointer())

    builder.call(pfn, [global_fmt, func.args[0]])
    builder.ret_void()


def emit_print_funcs(module):
    #intrinsics
    fnty = ir.FunctionType(ir.VoidType(), [ir.IntType(64),ir.IntType(8).as_pointer()])
    fn = ir.Function(module, fnty, name="llvm.lifetime.start")
    context.funcs.create("llvm.lifetime.start",{"func" : fn, "names" : [], "ret" : ir.VoidType(), "static" : True, "allocs" : {}})

    fnty = ir.FunctionType(ir.VoidType(), [ir.IntType(64),ir.IntType(8).as_pointer()])
    fn = ir.Function(module, fnty, name="llvm.lifetime.end")
    context.funcs.create("llvm.lifetime.end",{"func" : fn, "names" : [], "ret" : ir.VoidType(), "static" : True, "allocs" : {}})

    #actual print stuff
    fnty = ir.FunctionType(ir.IntType(32), [ir.IntType(8).as_pointer()], var_arg=True)
    fn = ir.Function(module, fnty, name="printf")
    context.funcs.create("printf",{"func" : fn, "names" : [], "ret" : ir.IntType(32), "static" : True, "allocs" : {}})

    emit_print_func(module, "print_uint", "%u", ir.IntType(32))
    emit_print_func(module, "print_ulong", "%lu", ir.IntType(64))
    emit_print_func(module, "print_int", "%d", ir.IntType(32))
    emit_print_func(module, "print_long", "%ld", ir.IntType(64))
    emit_print_func(module, "print_float", "%f", ir.DoubleType())
    emit_print_func(module, "print_double", "%f", ir.DoubleType())

module = None
def emit_module(unit,pas):
   global module
   global static_ctors
   if module == None:
      module = ir.Module(name="main")
      module.triple = binding.get_default_triple()
      if "PackageDeclaration" in unit:
          context.set_package(unit["PackageDeclaration"][0]["QualifiedIdentifier"][0])

   for t in unit["TypeDeclaration"]:
      assert "ClassDeclaration" in t
      emit_class(t["ClassDeclaration"][0],module,pas)

   if pas == "decl_type":
      for clz in context.classs.clzs:
          context.classs.set_class(clz)
          ident = "static." + context.classs.fqid()
          e = ir.GlobalVariable(module,context.classs.get_type(module,True),ident)
          e.linkage = "internal"
          context.globals.create(ident,e)

   if pas == "decl_methods":
       emit_print_funcs(module)

   if pas == "method_body":
      typo = ir.FunctionType(ir.VoidType(), [])
      func = ir.Function(module, typo, name="main")
      func.attributes.add("noinline")
      block = func.append_basic_block('bb')
      builder = Builder(block)
      for f in static_ctors:
        builder.call(f,[])

      builder.call(context.get("life.stel.e.test.TestClass.main")[0]["func"],[])

      builder.ret_void()

      print str(module).replace("s32","i32").replace("s16","i16").replace("s64","i64").replace("s8","i8")

