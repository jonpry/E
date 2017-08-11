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
      return funcs.funcs[fqid() + "." + name]

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

def set_package(p):
   global package
   package = p

def set_type(t,name):
   global clz
   clz['class_type'] = t;
   clz['class_name'] = name;

def fqid():
   global package
   global clz
   return package + "." + clz['class_name']

clzs = []
def new_class():
   global clzs
   clz = {'class_members' : {}, 'class_type' : None, 'class_name' : '', 'static_init' : None, 'init' : None}
   clzs.append(clz)
   return clz

clz = {'class_members' : {}}
class_stack = [{}]
class_pos = 0

def push_class(name):
   global clz
   global class_stack
   global class_pos
   class_pos += 1
   if class_pos >= len(class_stack):
      clz = new_class()
      class_stack.append({name : clz})
      return
   if name in class_stack[class_pos]: 
      clz = class_stack[class_pos][name]
      return
   clz = new_class()
   class_stack[class_pos][name] = clz


def pop_class():
   global clz
   global class_pos
   clz = new_class() #TODO
   class_pos-=1

def get_type():
   global clz
   return clz['class_type']

def get(var,builder=None):
   global context
   global clz

   fq = fqid() + "." + var
   if var in context:
      return context[var]
   if fq in globals.globals:
      return globals.globals[fq]
   if len(thiss.thiss) == 0 or thiss.thiss[-1] == None:
      return None

   this = thiss.thiss[-1]
   if var in clz['class_members']:
      i = clz['class_members'].keys().index(var)
      #print this
      v = builder.gep(this,[ir.Constant(ir.IntType(32),0),ir.Constant(ir.IntType(32),i)])
      return v

def set(var, val, builder=None):
   if var in context:
      context[var] = val
      return 
   print var
   assert(False)

def create_member(t,name):
   global clz
   assert(name not in clz['class_members'])
   clz['class_members'][name] = t

def get_member_types():
   global clz
   t = []
   for k,v in clz['class_members'].items():
     t.append(v)
   return t

def set_static_init(func):
   global clz
   clz['static_init'] = func

def set_init(func):
   global clz
   clz['init'] = func

def get_static_init():
   global clz
   return clz['static_init']

def get_init():
   global clz
   return clz['init']

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


