# -*- coding: utf-8 -*-
import os
import codecs
import json
from collections import OrderedDict
from llvmlite import ir
from llvmlite import binding



class Builder(ir.IRBuilder):
    def tounsigned(self, value):
        cls=ir.instructions.CastInstr
        instr = cls(self.block, 'bitcast', value, ir.IntType(value.type.width), '')
        self._insert(instr)
        return instr

    def tosigned(self, value):
        cls=ir.instructions.CastInstr
        instr = cls(self.block, 'bitcast', value, SIntType(value.type.width), '')
        self._insert(instr)
        return instr

class SIntType(ir.types.Type):
    """
    The type for integers.
    """
    null = '0'
    _instance_cache = {}

    def __new__(cls, bits):
        # Cache all common integer types
        if 0 <= bits <= 128:
            try:
                return cls._instance_cache[bits]
            except KeyError:
                inst = cls._instance_cache[bits] = cls.__new(bits)
                return inst
        return cls.__new(bits)

    @classmethod
    def __new(cls, bits):
        assert isinstance(bits, int) and bits >= 0
        self = super(SIntType, cls).__new__(cls)
        self.width = bits
        return self

    def __getnewargs__(self):
        return self.width,

    def __copy__(self):
        return self

    def _to_string(self):
        return 's%u' % (self.width,)

    def __eq__(self, other):
        if isinstance(other, SIntType):
            return self.width == other.width
        else:
            return False

    def __hash__(self):
        return hash(SIntType)

    def format_constant(self, val):
        if isinstance(val, bool):
            return str(val).lower()
        else:
            return str(val)

    @property
    def intrinsic_name(self):
        return str(self)

