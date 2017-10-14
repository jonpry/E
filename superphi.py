# -*- coding: utf-8 -*-
import copy
import sys
import traceback
from llvmlite import ir
from collections import OrderedDict
import emit, utils, ropes

class superphi:
  def __init__(self,builder,var):
    self.builder = builder
    if isinstance(var,tuple):
      self.type = (var[0].type,var[1].type)
      self.phi = (builder.phi(self.type[0]), builder.phi(self.type[1]))
    else:
      if isinstance(var,ir.Type):
        self.type = var
      else:
        self.type = var.type
      self.phi = builder.phi(self.type)

  def add_incoming(self,v,edge):
    if isinstance(v,tuple):
      self.phi[0].add_incoming(v[0],edge)
      self.phi[1].add_incoming(v[1],edge)
    else:
      self.phi.add_incoming(v,edge)

        
