# -*- coding: utf-8 -*-
import copy
from llvmlite import ir
from collections import OrderedDict

context = {}
cstack = []
globs = {}

def set_type(t):
   global class_type
   class_type = t;

def get_type():
   global class_type
   return class_type

def get(var,this=None,builder=None):
   global context
   global globs
   global class_members
   if var in context:
      return context[var]
   if var in globs:
      return globs[var]
   if this == None:
      return None

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

def create_global(name,val):
   global globs;
   assert(name not in globs)
   globs[name] = val;

def get_global(name):
   global globs;
   return globs[name]

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
