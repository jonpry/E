# -*- coding: utf-8 -*-
import copy
import sys
import traceback
from llvmlite import ir
from collections import OrderedDict
import emit

context = {}
cstack = []
package = ""

def is_pointer(var):
   if isinstance(var,ir.Type):
      st = var
   else:
      st = var.type
   return st.is_pointer

class funcs:
   funcs = {}
   func_stack = []

   @staticmethod
   def push(func):
     funcs.func_stack.append(func)

   @staticmethod
   def pop():
     funcs.func_stack.pop()

   @staticmethod
   def current():
     return funcs.func_stack[-1]

   @staticmethod
   def create(name,d):
     assert(name not in funcs.funcs)
     funcs.funcs[name] = d;

   @staticmethod
   def get_native(name):
      for f,v in funcs.funcs.items():
         if v['func'].name == name:
            return v['func']
      return None

   @staticmethod
   def get(name):
      if name in funcs.funcs:
         return funcs.funcs[name]

class globals:
   globals = {}

   @staticmethod   
   def create(name,val):
     assert(name not in globals.globals)
     globals.globals[name] = val;

   @staticmethod
   def get(name):
     return globals.globals[name]

class thiss:
   thiss = []

   @staticmethod
   def push(this):
      thiss.thiss.append(this)

   @staticmethod
   def pop():
      thiss.thiss.pop()

class breaks:
   breaks = []

   @staticmethod
   def push(tgt):
      breaks.breaks.append(tgt)

   @staticmethod
   def pop():
      breaks.breaks.pop()

   @staticmethod
   def get():
      return breaks.breaks[-1]

class continues:
   continues = []

   @staticmethod
   def push(tgt):
      continues.continues.append(tgt)

   @staticmethod
   def pop():
      continues.continues.pop()

   @staticmethod
   def get():
      return continues.continues[-1]

class classs:
   clzs = []
   clz = {'class_members' : {}}
   class_stack = [{}]

   @staticmethod
   def set_type(t,s,name):
      global package
      classs.clz['class_type'] = t;
      classs.clz['static_type'] = s;
      classs.clz['class_name'] = package + "." + name;

   @staticmethod
   def fqid():
      return classs.clz['class_name']

   @staticmethod   
   def new():
      classs.clz = {'class_members' : {}, "static_members" : {}, 'extends' : None, 'class_type' : None, "static_type" : None, 'constructor' : None, 'class_name' : '', 'static_init' : None, 'init' : None}
      classs.clzs.append(classs.clz)
      return classs.clz

   @staticmethod   
   def push(name):
      classs.clz = classs.get_class(name)
      if classs.clz == None:
         classs.clz = classs.new()
      classs.class_stack.append(classs.clz)

   @staticmethod   
   def pop():
      classs.class_stack.pop()
      clz = classs.class_stack[-1]

   @staticmethod   
   def set_constructor(func):
      classs.clz['constructor'] = func

   @staticmethod   
   def set_extends(sup):
      classs.clz['extends'] = sup

   @staticmethod   
   def get_extends():
      return classs.clz['extends']

   @staticmethod   
   def get_type(cl,module,static):
      if static:
         if cl['static_type'] != None:
            return cl['static_type']
      else: 
         if cl['class_type'] != None:
            return cl['class_type']

      t = module.context.get_identified_type(cl['class_name'])
      types = classs.get_member_types(cl,module,False)
      t.set_body(ir.IntType(8).as_pointer(), *types)
      cl['class_type'] = t

      s = module.context.get_identified_type(cl['class_name'] + ".static")
      types = classs.get_member_types(cl,module,True)
      s.set_body(*types)
      cl['static_type'] = s

      return classs.get_type(cl,module,static)

   @staticmethod   
   def get_class_fq(ident):
      for cls in classs.clzs:
         if cls["class_name"] == ident:
           return cls
      return None


   @staticmethod   
   def get_class(ident):
      global package
      c = classs.get_class_fq(ident)
      if c != None:
         return c
      ident = package + "." + ident
      return classs.get_class_fq(ident)
 
   @staticmethod   
   def get_class_type(ident):
      cls = classs.get_class(ident)
      return cls["class_type"]

   @staticmethod   
   def create_member(t,name,static):
      if static:
         assert(name not in classs.clz['static_members'])
         classs.clz['static_members'][name] = t
      else:
         assert(name not in classs.clz['class_members'])
         classs.clz['class_members'][name] = t

   @staticmethod   
   def get_member_types(clz,module,static):
      src = "class_members"
      if static:
         src = "static_members"
      t = []
      if not static and clz['extends'] != None:
        t.append(classs.get_type(clz['extends'],module,static))
      for k,v in clz[src].items():
        t.append(v)
      return t

   @staticmethod   
   def set_static_init(func):
      classs.clz['static_init'] = func

   @staticmethod   
   def set_init(func):
      classs.clz['init'] = func

   @staticmethod   
   def get_static_init():
      return classs.clz['static_init']

   @staticmethod   
   def get_init():
      return classs.clz['init']

def set_package(p):
   global package
   package = p

def gep(ptr,this,var,builder,static, extended):
   #print traceback.print_stack()
   src = "static_members" if static else "class_members"
   if var in this[src]:
      i = this[src].keys().index(var)
      if static == False:
         i += 1
      if static == False and extended == False and this['extends'] != None:
         i += 1
      #print "gep"
      #print traceback.print_stack()
      #print this
      if extended:
         v = builder.gep(ptr,[ir.Constant(ir.IntType(32),0),ir.Constant(ir.IntType(32),1),ir.Constant(ir.IntType(32),i)])
      else:
         v = builder.gep(ptr,[ir.Constant(ir.IntType(32),0),ir.Constant(ir.IntType(32),i)])
      return v

def get_one(var,obj,objclz,extended,builder):
   global context

   if var in context:
      return context[var]

   #print objclz
   #print var
   if funcs.get(var) != None:
      #print "png"
      return (funcs.get(var),None)

   if objclz == None:
      return None

   fq = objclz["class_name"] + "." + var
   #print var
   #print objclz
   #print fq
   sys.stdout.flush()
#   if fq in globals.globals:
#      return globals.globals[fq]
   if funcs.get(fq) != None:
      return (funcs.get(fq),obj)

   if var in objclz["static_members"]:
      return gep(globals.get("#static." + objclz["class_name"]),objclz,var,builder, True,False)
       
   if obj==None:
      return None
   return gep(obj,objclz,var,builder, False, extended)

def get_one_poly(var,obj,objclz,builder):
   t = get_one(var,obj,objclz,False,builder)
   if t != None:
      return t
   if objclz['extends'] != None:
      return get_one(var,obj,objclz['extends'],True,builder)

def get(var,builder=None,test=False):  
   thistype = classs.clz
   if len(thiss.thiss) == 0 or thiss.thiss[-1] == None:
      thisvar = None
   else:
      thisvar = thiss.thiss[-1]

   if test:
     print "type"
     print var

   t = get_one_poly(var,thisvar,thistype,builder)
   if t != None:
       return t      
   
   var = var.split(".")
   for i in range(len(var)):
     v = var[i]    
     e = get_one_poly(v,thisvar,thistype,builder) 
     if i == (len(var) - 1):
       if e == None and i==0:
           return classs.get_class_fq(package + "." + v)
       return e
     if e == None and i==0: #could be a class name
       thistype = classs.get_class_fq(package + "." + v)
     else:
       thisvar = e
       thistype = classs.get_class_fq(e.type.pointee.name)


def set(var, val, builder=None):
   if var in context:
      context[var] = val
      return 
   print var
   assert(False)

def create(var,v):
   global context
   assert(var not in context)
   context[var] = v

def items():
   global context
   return context.items()

def current():
   global context
   return context.copy()

def push(deep,force=None):
   #print "push"
   global context
   global cstack
   if force != None:
      ret = force.copy()
      context=force.copy()
   elif deep:
      ret = copy.deepcopy(context)
   else:
      ret = context.copy()
   cstack.append(ret)
   return ret.copy()

#returns items in both a and b that are different
def different_in(a,b):
   ret = []
   for k,v in a.items():
      if k in b:
        if v != b[k]:
          ret.append( (k,v,b[k]) )
   return ret

#returns items that went out of scope
def removed_in(a,b):
   ret = []
   for k,v in a.items():
      if k not in b:
         ret.append( (k,v) )
   return ret


def pop(builder):
   global context
   global cstack   
   #print "pop"

   ret = context.copy()
   context = cstack.pop().copy()

   #pop can only clear variables from scope, not change meaning
   for k,v, nv in different_in(context,ret):
      context[k] = nv

   diff = removed_in(ret,context)
   for n,t in diff:
      if is_pointer(t):
        if isinstance(t,ir.Argument):
           continue
        if n.startswith(".bb"):
           continue
        emit.emit_lifetime(t,t.type,'end',builder)

   return (context.copy(),diff)


