# -*- coding: utf-8 -*-
import copy

context = {}
cstack = []

def get(var):
   global context
   return context[var]

def set(var,v):
   global context
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

def pop():
   global context
   global cstack   
   context = cstack.pop()
  
