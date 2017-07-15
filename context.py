# -*- coding: utf-8 -*-
import copy
from llvmlite import ir
from collections import OrderedDict

context = {}
cstack = []
globs = {}
funcs = {}
package = ""

def create_func(name,d):
   global funcs
   assert(name not in funcs)
   funcs[name] = d;

def get_func(name):
   global funcs
   if name in funcs:
      return funcs[name]
   return funcs[fqid() + "." + name]

def set_package(p):
   global package
   package = p

def set_type(t,name):
   global class_type
   global class_name
   class_type = t;
   class_name = name;

def fqid():
   global package
   global class_name
   return package + "." + class_name

def push_class(name):
   pass

def pop_class():
   pass

def get_type():
   global class_type
   return class_type

def get(var,builder=None):
   global context
   global globs
   global class_members
   global thiss

   fq = fqid() + "." + var
   if var in context:
      return context[var]
   if fq in globs:
      return globs[fq]
   if len(thiss) == 0 or thiss[-1] == None:
      return None

   this = thiss[-1]
   if var in class_members:
      i = class_members.keys().index(var)
      v = builder.gep(this,[ir.Constant(ir.IntType(32),0),ir.Constant(ir.IntType(32),i)])
      return v

class_members = OrderedDict()
def create_member(t,name):
   global class_members
   assert(name not in class_members)
   class_members[name] = t

def get_member_types():
   global class_members
   t = []
   for k,v in class_members.items():
     t.append(v)
   return t

def create(var,v):
   global context
   assert(var not in context)
   context[var] = v

def items():
   global context
   return context.items()

def push(deep):
   global context
   global cstack
   if deep:
      cstack.append(copy.deepcopy(context))
   else:
      cstack.append(context.copy())

thiss = []
def push_this(this):
   global thiss
   thiss.append(this)

def pop_this():
   global thiss
   thiss.pop()

def create_global(name,val):
   global globs;
   assert(name not in globs)
   globs[name] = val;

def get_global(name):
   global globs;
   return globs[fqid() + "." + name]

def pop():
   global context
   global cstack   
   context = cstack.pop()

breaks = []
def push_break(tgt):
   global breaks
   breaks.append(tgt)

def pop_break():
   global breaks
   breaks.pop()

def get_break():
   global breaks
   return breaks[-1]
