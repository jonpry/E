#!/usr/bin/python
from llvmlite import ir
from signed import SIntType, Builder
import context

def type_info(a):
   signed = False
   flo = False
   if "i" in str(a):
     t = int(str(a).split("i")[1].split(' ')[0])
   elif "s" in str(a):
     t = int(str(a).split("s")[1].split(' ')[0])
     signed = True
   elif "float" in str(a):
     t = 32
     flo = True
   elif "double" in str(a):
     t = 64
     flo = True
   return (signed,flo,t)

def cast_ptr(v,t,builder):
   if v.type == t:
      return v
   typ = v.type.pointee.name
   while typ != None:
     clz = context.classs.get_class(typ)
     if clz['extends'] == None:
        break
     typ = clz['extends']['class_type'].name
     v = builder.gep(v,[ir.Constant(ir.IntType(32),0),ir.Constant(ir.IntType(32),1)])
     if v.type == t:
        return v
   return v

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
   if a.type == t:
     return a

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

