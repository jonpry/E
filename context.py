# -*- coding: utf-8 -*-
import copy
import sys
import traceback
from llvmlite import ir
from collections import OrderedDict

context = {}
cstack = []
package = ""

def is_pointer(var):
   return len(str(var.type).split("*")) > 1

class funcs:
   funcs = {}
   func_stack = []

   @staticmethod
   def push(func):
     funcs.func_stack.append(func)

   @staticmethod
   def pop():
     funcs.func_stack.pop()

   @staticmethod
   def current():
     return funcs.func_stack[-1]

   @staticmethod
   def create(name,d):
     assert(name not in funcs.funcs)
     funcs.funcs[name] = d;

   @staticmethod
   def get_native(name):
      for f,v in funcs.funcs.items():
         if v['func'].name == name:
            return v['func']
      return None

   @staticmethod
   def get(name):
      if name in funcs.funcs:
         return funcs.funcs[name]

class globals:
   globals = {}

   @staticmethod   
   def create(name,val):
     assert(name not in globals.globals)
     globals.globals[name] = val;

   @staticmethod
   def get(name):
     return globals.globals[name]

class thiss:
   thiss = []

   @staticmethod
   def push(this):
      thiss.thiss.append(this)

   @staticmethod
   def pop():
      thiss.thiss.pop()

class breaks:
   breaks = []

   @staticmethod
   def push(tgt):
      breaks.breaks.append(tgt)

   @staticmethod
   def pop():
      breaks.breaks.pop()

   @staticmethod
   def get():
      return breaks.breaks[-1]

class continues:
   continues = []

   @staticmethod
   def push(tgt):
      continues.continues.append(tgt)

   @staticmethod
   def pop():
      continues.continues.pop()

   @staticmethod
   def get():
      return continues.continues[-1]

class classs:
   clzs = []
   clz = {'class_members' : {}}
   class_stack = [{}]

   @staticmethod
   def set_type(t,s,name):
      global package
      classs.clz['class_type'] = t;
      classs.clz['static_type'] = s;
      classs.clz['class_name'] = package + "." + name;

   @staticmethod
   def fqid():
      return classs.clz['class_name']

   @staticmethod   
   def new():
      classs.clz = {'class_members' : {}, "static_members" : {}, 'class_type' : None, "static_type" : None, 'class_name' : '', 'static_init' : None, 'init' : None}
      classs.clzs.append(classs.clz)
      return classs.clz

   @staticmethod   
   def push(name):
      classs.clz = classs.get_class(name)
      if classs.clz == None:
         classs.clz = classs.new()
      classs.class_stack.append(classs.clz)

   @staticmethod   
   def pop():
      classs.class_stack.pop()
      clz = classs.class_stack[-1]

   @staticmethod   
   def get_type(static):
      if static:
         return classs.clz['static_type']
      return classs.clz['class_type']

   @staticmethod   
   def get_class_fq(ident):
      for cls in classs.clzs:
         if cls["class_name"] == ident:
           return cls
      return None


   @staticmethod   
   def get_class(ident):
      global package
      c = classs.get_class_fq(ident)
      if c != None:
         return c
      ident = package + "." + ident
      return classs.get_class_fq(ident)
 
   @staticmethod   
   def get_class_type(ident):
      cls = classs.get_class(ident)
      return cls["class_type"]

   @staticmethod   
   def create_member(t,name,static):
      if static:
         assert(name not in classs.clz['static_members'])
         classs.clz['static_members'][name] = t
      else:
         assert(name not in classs.clz['class_members'])
         classs.clz['class_members'][name] = t

   @staticmethod   
   def get_member_types(static):
      src = "class_members"
      if static:
         src = "static_members"
      t = []
      for k,v in classs.clz[src].items():
        t.append(v)
      return t

   @staticmethod   
   def set_static_init(func):
      classs.clz['static_init'] = func

   @staticmethod   
   def set_init(func):
      classs.clz['init'] = func

   @staticmethod   
   def get_static_init():
      return classs.clz['static_init']

   @staticmethod   
   def get_init():
      return classs.clz['init']

def set_package(p):
   global package
   package = p

def gep(ptr,this,var,builder,static):
   #print traceback.print_stack()
   src = "static_members" if static else "class_members"
   if var in this[src]:
      i = this[src].keys().index(var)
      #print "gep"
      #print traceback.print_stack()
      #print this
      v = builder.gep(ptr,[ir.Constant(ir.IntType(32),0),ir.Constant(ir.IntType(32),i)])
      return v

def get_one(var,obj,objclz,builder):
   global context

   if var in context:
      return context[var]

   #print var
   if funcs.get(var) != None:
      #print "png"
      return (funcs.get(var),None)

   if objclz == None:
      return None

   fq = objclz["class_name"] + "." + var
   #print var
   #print objclz
   #print fq
   sys.stdout.flush()
#   if fq in globals.globals:
#      return globals.globals[fq]
   if funcs.get(fq) != None:
      return (funcs.get(fq),obj)

   if var in objclz["static_members"]:
      return gep(globals.get("static." + objclz["class_name"]),objclz,var,builder, True)
       
   if obj==None:
      return None
   return gep(obj,objclz,var,builder, False)

def get(var,builder=None):  
   thistype = classs.clz
   if len(thiss.thiss) == 0 or thiss.thiss[-1] == None:
      thisvar = None
   else:
      thisvar = thiss.thiss[-1]

   #print "type"
   #print thistype

   t = get_one(var,thisvar,thistype,builder)
   if t != None:
       return t      
   
   var = var.split(".")
   for i in range(len(var)):
     v = var[i]    
     e = get_one(v,thisvar,thistype,builder) 
     if i == (len(var) - 1):
        return e
     if e == None and i==0: #could be a class name
       thistype = classs.get_class_fq(package + "." + v)
     else:
       thisvar = e
       thistype = classs.get_class_fq(str(e.type).split("\"")[1])


def set(var, val, builder=None):
   if var in context:
      context[var] = val
      return 
   print var
   assert(False)

def create(var,v):
   global context
   assert(var not in context)
   context[var] = v

def items():
   global context
   return context.items()

def current():
   global context
   return context.copy()

def push(deep,force=None):
   #print "push"
   global context
   global cstack
   if force != None:
      ret = force.copy()
      context=force.copy()
   elif deep:
      ret = copy.deepcopy(context)
   else:
      ret = context.copy()
   cstack.append(ret)
   return ret.copy()

def different_in(a,b):
   ret = []
   for k,v in a.items():
      if k in b:
        if v != b[k]:
          ret.append( (k,v,b[k]) )
   return ret

def pop():
   global context
   global cstack   
   #print "pop"

   ret = context.copy()
   context = cstack.pop().copy()

   #pop can only clear variables from scope, not change meaning
   for k,v, nv in different_in(context,ret):
      context[k] = nv
   return context.copy()


