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

   s = ir.Constant(emit.string_type, [data.bitcast(emit.rtti_type.as_pointer()),None,None,None,fmt_bytes.type.count,None,global_fmt.bitcast(ir.IntType(8).as_pointer())])
   a = ir.Constant(emit.string_alloc_type, [None,s])
   data.initializer = a
  
   data = data.gep([ir.Constant(ir.IntType(32),1)])

   stringtab[s] = data

   return data
