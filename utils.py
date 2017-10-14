# -*- coding: utf-8 -*-
import copy
import sys
import traceback
from llvmlite import ir
from collections import OrderedDict
import emit,context

def make_bytearray(buf):
    """
    Make a byte array constant from *buf*.
    """
    b = bytearray(buf)
    n = len(b)
    return ir.Constant(ir.ArrayType(ir.IntType(8), n), b)

def global_constant(module, name, value):
    """
    Get or create a (LLVM module-)global constant with *name* or *value*.
    """
    data = ir.GlobalVariable(module,value.type,name)
    data.global_constant = True
    data.initializer = value
    return data


def sizeof(t,builder):
   if not context.is_pointer(t):
      t = t.as_pointer()
   foo = builder.inttoptr(ir.Constant(ir.IntType(64),0),t)
   ofst = builder.gep(foo,[ir.Constant(ir.IntType(32),1), ir.Constant(ir.IntType(32),0)])
   ofst = builder.ptrtoint(ofst,ir.IntType(32))
   return ofst
