# -*- coding: utf-8 -*-
import copy
import sys
import traceback
from llvmlite import ir
from collections import OrderedDict
import emit, utils, ropes

stringtab = {}

def local_string(rope,builder):

   string = builder.alloca(emit.string_alloc_type)
   string_const = ir.Constant(emit.string_type, [ir.Constant(ir.IntType(32),0),rope])
   stringa_const = ir.Constant(emit.string_alloc_type, [None,string_const])
   builder.store(stringa_const,string)
   
   aptr = builder.gep(string,[ir.Constant(ir.IntType(32),0),ir.Constant(ir.IntType(32),1)])
   aptr = builder.gep(aptr,[ir.Constant(ir.IntType(32),0),ir.Constant(ir.IntType(32),0)])


   store = builder.store(utils.sizeof(emit.rtti_type,builder),aptr)

   string = builder.gep(string,[ir.Constant(ir.IntType(32),0),ir.Constant(ir.IntType(32),1)])
   return string

def create(name,s,builder):
   if s in stringtab:
       return stringtab[s]

   module = builder.module

   fmt_bytes = utils.make_bytearray(s.encode('ascii'))
   global_fmt = utils.global_constant(module, "#stringtab_bytes." + name, fmt_bytes)

   rope = ir.GlobalVariable(module,emit.rope_alloc_type,"#stringtab_ropes." + name)
   rope.global_constant = True

   rope_const = ir.Constant(emit.rope_type, [None,None,None,None,fmt_bytes.type.count,None,global_fmt.bitcast(ir.IntType(8).as_pointer())])
   ropea_const = ir.Constant(emit.rope_alloc_type, [None,rope_const])
   rope.initializer = ropea_const
   rope.global_constant = True
  
   rope = rope.gep([ir.Constant(ir.IntType(32),0),ir.Constant(ir.IntType(32),1)])

   stringtab[s] = rope
   return rope

def raw_cstr(rope,builder):
   #rope = builder.gep(string, [ir.Constant(ir.IntType(32),0),ir.Constant(ir.IntType(32),1)])
   #rope = builder.load(rope)

   cstr = builder.gep(rope,[ir.Constant(ir.IntType(32),0),ir.Constant(ir.IntType(32),6)])
   return builder.load(cstr)

