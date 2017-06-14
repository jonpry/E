#!/usr/bin/python

from JavaLexer import JavaLexer
from JavaParser import JavaParser
from JavaListener import JavaListener
import antlr4
from antlr4.tree.Tree import TerminalNodeImpl, ErrorNodeImpl, TerminalNode, INVALID_INTERVAL
from llvmlite import ir
from llvmlite import binding
from ast import *

        #Antlr node type, 			symbol type for terminals,  ast object, 	types to collect
ops = { (TerminalNodeImpl, 			JavaParser.Identifier	) : [(Identifier, 	[])],
        (JavaParser.QualifiedNameContext,				) : [(QualifiedName, 	[(Identifier,)])],
        (JavaParser.ImportDeclarationContext,				) : [(ImportDecl, 	[(QualifiedName,),(TerminalNodeImpl,JavaParser.MUL)])],
        (JavaParser.PackageDeclarationContext,				) : [(PackageDecl, 	[(QualifiedName,)])],
        (JavaParser.ClassDeclarationContext,				) : [(ClassDecl, 	[(Identifier,),(ClassBody,)])],
        (JavaParser.ClassBodyContext,					) : [(ClassBody, 	[(ClassBodyDecl,)])],
        (JavaParser.ClassBodyDeclarationContext,			) : [(Block, 		[(Block,)]),
									     (MemberDecl,	[(MemberDecl,)])],
        (JavaParser.BlockContext,					) : [(Block, 		[(BlockStatement,)])],
        (JavaParser.MemberDeclarationContext,				) : [(MemberDecl, 	[(MemberDecl,)])],
        (JavaParser.MethodDeclarationContext,				) : [(MethodDecl,	[(Block,)])],
        (JavaParser.ConstructorDeclarationContext,			) : [(ConstructorDecl,	[(Block,)])],
        (JavaParser.FieldDeclarationContext,				) : [(FieldDecl,	[])],
        (JavaParser.EnumDeclarationContext,				) : [(EnumDecl,		[])],
        (JavaParser.InterfaceDeclarationContext,			) : [(InterfaceDecl,	[])],
        (JavaParser.MethodBodyContext,					) : [(Block,		[(Block,)])],
        (JavaParser.ConstructorBodyContext,				) : [(Block,		[(Block,)])],
        (JavaParser.BlockStatementContext,				) : [(BlockStatement,	[(LocalDecl,),(TypeDecl,),(Statement,)])],
        (JavaParser.StatementContext,					) : [(Block,		[(Block,)])],
	(JavaParser.LocalVariableDeclarationStatementContext,		) : [(LocalDecl,	[])],
        (JavaParser.TypeDeclarationContext,				) : [(ClassDecl, 	[(ClassDecl,)]),
									     (EnumDecl, 	[(EnumDecl,)])],
        (JavaParser.CompilationUnitContext,				) : [(CompilationUnit, 	[(PackageDecl,),(ImportDecl,),(TypeDecl,)])]  }

def explore(ctx,indent):
    if isinstance(ctx,TerminalNodeImpl):
        dn = (TerminalNodeImpl,ctx.getSymbol().type)
        if dn in ops:
          return ops[dn][0][0]([ctx.getSymbol()])

    #can't descend on terminals 
    if isinstance(ctx,TerminalNodeImpl):
       return

    #print_indent(JavaParser.ruleNames[ctx.getRuleIndex()],indent)
    #first pass, do conversions
    nca = []
    for c in ctx.children:
       nc = explore(c,indent+1)
       if nc != None:
          nca.append(nc)
       else:
          nca.append(c)
    ctx.children = nca

    dn = (type(ctx),)
    if dn in ops:
       for possible in ops[dn]:
         collect = possible[1]
         collected = []
         for c in ctx.children:
            for t in collect:
              doit = False
              if t[0] == TerminalNodeImpl and type(c) == TerminalNodeImpl:
                  doit = c.getSymbol().type == t[1]
              elif isinstance(c,t[0]):
                  doit = True 
                  #if type(c) == ClassDecl:
                     #print "foudn: " + str(t[0]) + ", " + str(type(c)) + ", " + str(dn) + ", " + str(possible)
              if doit:
                 collected.append(c)
         #print "mk" + str(possible[0])
         if len(collected) > 0 or len(ops[dn]) < 2:
           return possible[0](collected)
    #print "no ops" + str(type(ctx))
    return
"""
    print_indent(JavaParser.ruleNames[ctx.getRuleIndex()],indent)
    #first pass, do conversions
    nca = []
    for c in ctx.children:
       nc = explore(c,indent+1)
       if nc != None:
          nca.append(nc)
       else:
          nca.append(c)
    ctx.children = nca
"""


def main():
    lexer = JavaLexer(antlr4.StdinStream())
    stream = antlr4.CommonTokenStream(lexer)
    parser = JavaParser(stream)
    tree = parser.compilationUnit()
    #listener = Listener("foo.java")
    #walker = antlr4.ParseTreeWalker()
    #walker.walk(listener, tree)
    print explore(tree,0)

    #listener.typecheck()
    #print str(listener.emit())

if __name__ == '__main__':
    main()
