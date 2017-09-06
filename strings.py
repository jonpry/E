# -*- coding: utf-8 -*-
import copy
import sys
import traceback
from llvmlite import ir
from collections import OrderedDict
import emit, utils, ropes

stringtab = {}

def local_string(rope,builder):

   string = builder.alloca(emit.string_type)
   string_const = ir.Constant(emit.string_type, [rope])
   builder.store(string_const,string)

   stringa_const = ir.Constant(emit.rtti_type, [None,None,None])   
   stringa = builder.alloca(emit.rtti_type)
   builder.store(stringa_const,stringa)

   return (stringa,string)

def create(name,s,builder):
   if s in stringtab:
       return local_string(stringtab[s], builder)

   module = builder.module

   fmt_bytes = utils.make_bytearray(s.encode('ascii'))
   global_fmt = utils.global_constant(module, "#stringtab_bytes." + name, fmt_bytes)

   ropea = ir.GlobalVariable(module,emit.rtti_type,"#stringtab_rtti." + name)
   ropea.global_constant = True
   ropea_const = ir.Constant(emit.rtti_type, [None,None,None])
   ropea.initializer = ropea_const

   rope = ir.GlobalVariable(module,emit.rope_type,"#stringtab_ropes." + name)
   rope_const = ir.Constant(emit.rope_type, [None,None,None,fmt_bytes.type.count,None,global_fmt.bitcast(ir.IntType(8).as_pointer())])
   rope.global_constant = True
   rope.initializer = rope_const
  
   stringtab[s] = rope
   return local_string(rope,builder)

def raw_cstr(string,builder):
   rope = builder.gep(string, [ir.Constant(ir.IntType(32),0),ir.Constant(ir.IntType(32),0)],inbounds=True)
   rope = builder.load(rope)

   cstr = builder.gep(rope,[ir.Constant(ir.IntType(32),0),ir.Constant(ir.IntType(32),5)],inbounds=True)
   return builder.load(cstr)

