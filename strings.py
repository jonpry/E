# -*- coding: utf-8 -*-
import copy
import sys
import traceback
from llvmlite import ir
from collections import OrderedDict
import emit, utils, ropes, context
from signed import SIntType, Builder

stringtab = {}

def local_string(rope,builder):

   string = builder.alloca(emit.string_type)
   stringa = builder.alloca(emit.rtti_type)

   return local_init((string,stringa),rope,builder)

def local_init(memory, rope,builder):

   string = memory[0]
   string_const = ir.Constant(emit.string_type, [rope[1],rope[0]])
   builder.store(string_const,string)

   stringa_const = ir.Constant(emit.rtti_type, [None,None,None])   
   stringa = memory[1]
   builder.store(stringa_const,stringa)

   return (string,stringa)


def init(memory,s,builder):
   assert(s in stringtab)
   return local_init(memory, stringtab[s], builder)

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
  
   ropet = (rope,ropea)
   stringtab[s] = ropet 
   return local_string(ropet,builder)

def raw_cstr(string,builder):
   rope = builder.gep(string, [ir.Constant(ir.IntType(32),0),ir.Constant(ir.IntType(32),1)],inbounds=True)
   rope = builder.load(rope)

   cstr = builder.gep(rope,[ir.Constant(ir.IntType(32),0),ir.Constant(ir.IntType(32),5)],inbounds=True)
   return builder.load(cstr)

def emit_print(module):
    name = "print_string"
    func = context.funcs.get_native(name)
    if func == None:
       fnty = ir.FunctionType(ir.VoidType(), [emit.string_type.as_pointer(),emit.rtti_type.as_pointer()])
       func = ir.Function(module, fnty, name=name)
       func.attributes.add("noinline")
       context.funcs.create(name,{"func" : func, "names" : ["v"], "ret" : ir.VoidType(), "static" : True, "native" : True, "allocs" : {}})
    
    block = func.append_basic_block('bb')
    builder = Builder(block)
    pfn = context.get("printf")['func']["func"]

    #create global for string
    global_fmt = create("print_" + name.split("_")[1] + "_format", '%s\n\00', builder)[0]
    global_fmt = raw_cstr(global_fmt,builder)

    builder.call(pfn, [global_fmt, raw_cstr(func.args[0],builder)])
    builder.ret_void()


