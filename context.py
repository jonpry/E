# -*- coding: utf-8 -*-
import copy
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
      return funcs.funcs[classs.fqid() + "." + name]

class globals:
   globals = {}

   @staticmethod   
   def create(name,val):
     assert(name not in globals.globals)
     globals.globals[name] = val;

   @staticmethod
   def get(name):
     return globals.globals[fqid() + "." + name]

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
   def set_type(t,name):
      global package
      classs.clz['class_type'] = t;
      classs.clz['class_name'] = package + "." + name;

   @staticmethod
   def fqid():
      return classs.clz['class_name']

   @staticmethod   
   def new():
      classs.clz = {'class_members' : {}, 'class_type' : None, 'class_name' : '', 'static_init' : None, 'init' : None}
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
   def get_type():
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
   def create_member(t,name):
      assert(name not in classs.clz['class_members'])
      classs.clz['class_members'][name] = t

   @staticmethod   
   def get_member_types():
      t = []
      for k,v in classs.clz['class_members'].items():
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

def gep(ptr,this,var,builder):
   if var in this['class_members']:
      i = this['class_members'].keys().index(var)
      #print this
      v = builder.gep(ptr,[ir.Constant(ir.IntType(32),0),ir.Constant(ir.IntType(32),i)])
      return v

def get_one(var,builder):
   global context

   if var in context:
      return context[var]
   fq = classs.fqid() + "." + var
   if fq in globals.globals:
      return globals.globals[fq]
   if len(thiss.thiss) == 0 or thiss.thiss[-1] == None:
      return None

   this = thiss.thiss[-1]
   return gep(this,classs.clz,var,builder)

def get(var,builder=None):  
   t = get_one(var,builder) 
   if t != None:
      return t

   v = var.split(".")[0]
   t = get_one(v,builder) 
   if t != None:
      return gep(t,classs.get_class(str(t.type).split("\"")[1]),var.split(".")[1],builder)
   print var
   print v
   assert(False)

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


