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

   rope = ir.GlobalVariable(module,emit.rope_alloc_type,"#stringtab_ropes." + name)
   rope.global_constant = True

   rope_const = ir.Constant(emit.rope_type, [rope.bitcast(emit.rtti_type.as_pointer()),None,None,None,fmt_bytes.type.count,None,global_fmt.bitcast(ir.IntType(8).as_pointer())])
   ropea_const = ir.Constant(emit.rope_alloc_type, [None,rope_const])
   rope.initializer = ropea_const
   rope.global_constant = True
  
   rope = rope.gep([ir.Constant(ir.IntType(32),0),ir.Constant(ir.IntType(32),1)])

   string = ir.GlobalVariable(module,emit.string_alloc_type,"#stringtab." + name)
   string_const = ir.Constant(emit.string_type, [string.bitcast(emit.rtti_type.as_pointer()),rope])
   stringa_const = ir.Constant(emit.string_alloc_type, [None,string_const])
   string.initializer = stringa_const
   string.global_constant = True

   string = string.gep([ir.Constant(ir.IntType(32),0),ir.Constant(ir.IntType(32),1)])

   stringtab[s] = string
   return string

def raw_cstr(string,builder):
   rope = builder.gep(string, [ir.Constant(ir.IntType(32),0),ir.Constant(ir.IntType(32),1)])
   rope = builder.load(rope)

   string = builder.gep(rope,[ir.Constant(ir.IntType(32),0),ir.Constant(ir.IntType(32),6)])
   return builder.load(string)
