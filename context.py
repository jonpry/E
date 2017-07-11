# -*- coding: utf-8 -*-
import copy

context = {}
cstack = []
globs = {}

def get(var):
   global context
   global globs
   if var in context:
      return context[var]
   return globs[var]

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
