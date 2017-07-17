# -*- coding: utf-8 -*-
import copy
from llvmlite import ir
from collections import OrderedDict

context = {}
cstack = []
globs = {}
funcs = {}
func_stack = []
package = ""

def push_func(func):
   global func_stack
   func_stack.append(func)

def pop_func():
   global func_stack
   func_stack.pop()

def current_func():
   global func_stack
   return func_stack[-1]

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
   global clz
   clz['class_type'] = t;
   clz['class_name'] = name;

def fqid():
   global package
   global clz
   return package + "." + clz['class_name']

def new_class():
   return {'class_members' : {}, 'class_type' : None, 'class_name' : ''}

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
   global globs
   global clz
   global thiss

   fq = fqid() + "." + var
   if var in context:
      return context[var]
   if fq in globs:
      return globs[fq]
   if len(thiss) == 0 or thiss[-1] == None:
      return None

   this = thiss[-1]
   if var in clz['class_members']:
      i = clz['class_members'].keys().index(var)
      v = builder.gep(this,[ir.Constant(ir.IntType(32),0),ir.Constant(ir.IntType(32),i)])
      return v

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
