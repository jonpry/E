
import sys

from llvmlite import ir


next_serial = 1


class QualifiedName(object):
    def __init__(self, data):
        st = ""
        for d in data:
           st += str(d.data) + "."
        st = st[:-1]
        #print st
        self.data = st

    def emit(self, stack):
        yield str(self.__repr__())

    def __repr__(self):
        return self.data

class Identifier(object):
    def __init__(self, data):
        self.data = data[0].text

    def emit(self, stack):
        yield str(self.__repr__())

    def __repr__(self):
        return 'Identifier "%s"' % (self.data)

class CompilationUnit(object):
    def __init__(self, data):
        self.data = data

    def emit(self, stack):
        yield str(self.__repr__())

    def __repr__(self):
        return 'Unit "%s"' % (self.data)


class PackageDecl(object):
    def __init__(self, data):
        self.name = data[0]

    def emit(self, stack):
        stack.append(str(self.__repr__()))

    def __repr__(self):
        return 'Package "%s"' % (self.name,)

class ClassBody(object):
    def __init__(self, data):
        self.data = data
        #print data

    def emit(self, stack):
        stack.append(str(self.__repr__()))

    def __repr__(self):
        return 'Body "%s"' % (self.data,)

class ClassBodyDecl(object):
    pass

class Block(ClassBodyDecl):
    def __new__(cls,data):
       if len(data) > 0:
         if type(data[0]) == cls:
            return data[0]
       return super(Block, cls).__new__(cls)

    def __init__(self, data):
        if hasattr(self,"data"):
          return
        self.data = data
        #print data

    def emit(self, stack):
        stack.append(str(self.__repr__()))

    def __repr__(self):
        return 'Block "%s"' % (self.data,)

class BlockStatement(object):
    def __init__(self, data):
        self.data = data
        #print data

    def emit(self, stack):
        stack.append(str(self.__repr__()))

    def __repr__(self):
        return 'BlockStatement "%s"' % (self.data,)


class LocalDecl(object):
    def __init__(self, data):
        self.data = data
        #print data

    def emit(self, stack):
        stack.append(str(self.__repr__()))

    def __repr__(self):
        return 'LocalDecl "%s"' % (self.data,)

class MemberDecl(ClassBodyDecl):
    def __new__(cls,data):
       if len(data) > 0:
         if isinstance(data[0],cls):
            return data[0]
       return super(MemberDecl, cls).__new__(cls)

    def __init__(self, data):
       if hasattr(self,"data"):
         return
       self.data = data

    def emit(self, stack):
        stack.append(str(self.__repr__()))

    def __repr__(self):
        return 'MemberDecl "%s"' % (self.data,)

class MethodDecl(MemberDecl):
    def __new__(cls,data):
       if len(data) > 0:
         if type(data[0]) == cls:
            return data[0]
       return super(MethodDecl, cls).__new__(cls,data)

    def __init__(self, data):
       if hasattr(self,"data"):
         return
       self.data = data

    def emit(self, stack):
        stack.append(str(self.__repr__()))

    def __repr__(self):
        return 'MethodDecl "%s"' % (self.data,)

class FieldDecl(MemberDecl):
    def __new__(cls,data):
       if len(data) > 0:
         if type(data[0]) == cls:
            return data[0]
       return super(FieldDecl, cls).__new__(cls,data)

    def __init__(self, data):
       if hasattr(self,"data"):
         return
       self.data = data

    def emit(self, stack):
        stack.append(str(self.__repr__()))

    def __repr__(self):
        return 'FieldDecl "%s"' % (self.data,)

class ConstructorDecl(MemberDecl):
    def __new__(cls,data):
       if len(data) > 0:
         if type(data[0]) == cls:
            return data[0]
       return super(ConstructorDecl, cls).__new__(cls,data)

    def __init__(self, data):
       if hasattr(self,"data"):
         return
       self.data = data

    def emit(self, stack):
        stack.append(str(self.__repr__()))

    def __repr__(self):
        return 'ConstructorDecl "%s"' % (self.data,)

class EnumDecl(MemberDecl):
    def __new__(cls,data):
       if len(data) > 0:
         if type(data[0]) == cls:
            return data[0]
       return super(EnumDecl, cls).__new__(cls,data)

    def __init__(self, data):
       if hasattr(self,"data"):
         return
       self.data = data

    def emit(self, stack):
        stack.append(str(self.__repr__()))

    def __repr__(self):
        return 'EnumDecl "%s"' % (self.data,)

class InterfaceDecl(MemberDecl):
    def __new__(cls,data):
       if len(data) > 0:
         if type(data[0]) == cls:
            return data[0]
       return super(InterfaceDecl, cls).__new__(cls,data)

    def __init__(self, data):
       if hasattr(self,"data"):
         return
       self.data = data

    def emit(self, stack):
        stack.append(str(self.__repr__()))

    def __repr__(self):
        return 'InterfaceDecl "%s"' % (self.data,)

class ImportDecl(object):
    def __init__(self, data):
        self.name = data[0]
        self.wildcard = len(data) > 1

    def emit(self, stack):
        stack.append(str(self.__repr__()))

    def __repr__(self):
        return 'Import "%s %s"' % (self.name, str(self.wildcard))

class TypeDecl(object):
    pass

class ClassDecl(TypeDecl,MemberDecl):
    def __new__(cls,data):
       if len(data) > 0:
         if type(data[0]) == cls:
            return data[0]
       return super(ClassDecl, cls).__new__(cls,data)

    def __init__(self, data):
       if hasattr(self,"data"):
         return
       if len(data) > 0:
         if type(data[0]) == type(self):
           self = data[0]
           return
       self.data = data
       #print data[0].data

    def emit(self, stack):
        stack.append(str(self.__repr__()))

    def __repr__(self):
        return "Class: " + str(self.data)

class EnumDecl(TypeDecl):
    def __new__(cls,data):
       if len(data) > 0:
         if type(data[0]) == cls:
            return data[0]
       return super(EnumDecl, cls).__new__(cls)

    def __init__(self, data):
       if hasattr(self,"data"):
         return
       if len(data) > 0:
         if type(data[0]) == type(self):
           self = data[0]
           return
       self.data = data
       print data

    def emit(self, stack):
        stack.append(str(self.__repr__()))

    def __repr__(self):
        return "Class: " + str(self.data)


class ConstantString(object):
    def __init__(self, data):
        data = data[1:-1]
        self.data = data.replace('\\\"', '\"') + '\0'

    def typecheck(self, symboltable):
        pass

    def emit(self, builder, stack):
        global next_serial
        name = 'string_constant_%d' % (next_serial)
        next_serial += 1

        t = ir.ArrayType(ir.IntType(8), len(self.data))
        glob = ir.GlobalVariable(builder.module, t, name=name)
        glob.global_constant = True
        glob.initializer = ir.Constant(t, bytearray(self.data, 'utf-8'))
        z = ir.Constant(ir.IntType(32), 0)
        g = builder.gep(glob, [z, z])
        stack.append(g)
    
    def __repr__(self):
        return 'string "%s"' % (self.data)

class ConstantInt(object):
    def __init__(self, value):
        self.value = value

    def typecheck(self, symboltable):
        pass

    def emit(self, builder, stack):
        i = ir.Constant(ir.IntType(32), self.value)
        stack.append(i)

class ConstantFloat(object):
    def __init__(self, value):
        self.value = value

    def typecheck(self, symboltable):
        pass

    def emit(self, builder, stack):
        i = ir.Constant(ir.FloatType(), self.value)
        stack.append(i)

class Var(object):
    def __init__(self, name):
        self.name = name

    def typecheck(self, symboltable):
        self.item = symboltable[self.name]

    def emit(self, builder, stack):
        pass

    def fetch(self, builder, stack):
        self.item.fetch(builder, stack)

    def call(self, builder, stack):
        self.item.call(builder, stack)

    def reference(self, builder):
        return self.item.reference(builder)

    def __repr__(self):
        return 'var %s' % (self.name)

class Member(object):
    def __init__(self, target, name):
        self.target = target
        self.name = name

    def typecheck(self, symboltable):
        self.target.typecheck(symboltable)
        self.item = self.target.item.type.members[self.name]
        self.index = list(self.target.item.type.members.keys()).index(self.name)

    def emit(self, builder, stack):
        g = self.reference(builder)
        stack.append(builder.load(g))

    def reference(self, builder):
        z = ir.Constant(ir.IntType(32), 0)
        i = ir.Constant(ir.IntType(32), self.index)
        g = builder.gep(self.target.item.item, [z, i])
        return g

    def __repr__(self):
        return 'member %s.%s' % (str(self.target), self.name)

class Call(object):
    def __init__(self, func, args):
        self.func = func
        self.args = args

    def typecheck(self, symboltable):
        self.func.typecheck(symboltable)
        for a in self.args:
            a.typecheck(symboltable)

    def emit(self, builder, stack):
        for a in self.args:
            a.emit(builder, stack)
        self.func.call(builder, stack)

    def __repr__(self):
        return 'call %s' % (str(self.func))

class VarDecl(object):
    def __init__(self, name, _type):
        self.name = name
        self.type = _type

    def typecheck(self, symboltable):
        self.type = symboltable[self.type]
        symboltable[self.name] = self
    
    def emit(self, builder, stack):
        self.item = builder.alloca(self.type.type)
        stack.append(builder.load(self.item))

    def fetch(self, builder, stack):
        stack.append(builder.load(self.item))

    def reference(self, builder):
        return self.item

class Assignment(object):
    def __init__(self, target, value):
        self.target = target
        self.value = value

    def typecheck(self, symboltable):
        self.target.typecheck(symboltable)
        self.value.typecheck(symboltable)

    def emit(self, builder, stack):
        t = self.target.reference(builder)
        self.value.emit(builder, stack)
        v = stack.pop()
        builder.store(v, t)

class Struct(object):
    def __init__(self, name, members):
        self.name = name
        self.members = members

    def typecheck(self, typemap):
        for _, m in self.members.items():
            m.typecheck(typemap)

        self.type = ir.LiteralStructType(m.type.type for _, m in self.members.items())
    
    def emit(self, module):
        pass

class Function(object):
    def __init__(self, name, args, body, symboltable):
        self.name = name
        self.args = args
        self.body = body
        self.symboltable = SymbolTable(symboltable)

    def typecheck(self, typemap):
        for n, a in self.args.items():
            a.typecheck(typemap)
            self.symboltable[n] = a

        for b in self.body:
            b.typecheck(self.symboltable)

    def emit(self, module):
        self.type = ir.FunctionType(ir.VoidType(), (a.type.type for _, a in self.args.items()), False)
        self.func = ir.Function(module, self.type, self.name)
        block = self.func.append_basic_block('entry')
        builder = ir.IRBuilder(block)
        for a, i in zip(self.args.values(), self.func.args):
            t = builder.alloca(a.type.type)
            builder.store(i, t)
            a.item = t
        stack = []
        for b in self.body:
            b.emit(builder, stack)
        builder.ret_void()

    def call(self, builder, stack):
        count = len(self.func.args)
        args = stack[-count:]
        del stack[-count:]
        stack.append(builder.call(self.func, args))

class CFunction(object):
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def typecheck(self, typemap):
        for _, a in self.args.items():
            a.typecheck(typemap)

        self.type = ir.FunctionType(ir.VoidType(), (a.type.type for _, a in self.args.items()), False)

    def emit(self, module):
        self.func = ir.Function(module, self.type, self.name)

    def call(self, builder, stack):
        count = len(self.func.args)
        args = stack[-count:]
        del stack[-count:]
        stack.append(builder.call(self.func, args))
