# -*- coding: utf-8 -*-
import copy
import sys
import traceback
from llvmlite import ir
from collections import OrderedDict
import emit, utils, ropes

stringtab = {}

def create(name,s,module):
   if s in stringtab:
       return stringtab[s]

   fmt_bytes = utils.make_bytearray(s.encode('ascii'))
   global_fmt = utils.global_constant(module, "#stringtab_bytes." + name, fmt_bytes)

   data = ir.GlobalVariable(module,emit.string_alloc_type,"#stringtab." + name)
   data.global_constant = True

   struct = ir.Constant(emit.string_type, [data.bitcast(emit.rtti_type.as_pointer()),None,None,None,fmt_bytes.type.count,None,global_fmt.bitcast(ir.IntType(8).as_pointer())])
   a = ir.Constant(emit.string_alloc_type, [None,struct])
   data.initializer = a
   data.global_constant = True
  
   data = data.gep([ir.Constant(ir.IntType(32),0),ir.Constant(ir.IntType(32),1)])
   stringtab[s] = data

   return data

def raw_cstr(string,builder):
   string = builder.gep(string, [ir.Constant(ir.IntType(32),0),ir.Constant(ir.IntType(32),6)])
   return builder.load(string)
