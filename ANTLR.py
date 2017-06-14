#!/usr/bin/python

from ANTLRv4Lexer import ANTLRv4Lexer
from ANTLRv4Parser import ANTLRv4Parser
from ANTLRv4ParserListener import ANTLRv4ParserListener
import antlr4
from antlr4.tree.Tree import TerminalNodeImpl, ErrorNodeImpl, TerminalNode, INVALID_INTERVAL
from llvmlite import ir
from llvmlite import binding


def main():
    lexer = ANTLRv4Lexer(antlr4.StdinStream())
    stream = antlr4.CommonTokenStream(lexer)
    parser = ANTLRv4Parser(stream)
    rules = parser.grammarSpec().rules().ruleSpec()
    for rule in rules:
      spec = rule.parserRuleSpec()
      if spec == None:
         continue
      rule_name = spec.RULE_REF()
      alts = spec.ruleBlock().ruleAltList().labeledAlt()
      alts = [alt.alternative().element() for alt in alts]
      print alts
    #listener.typecheck()
    #print str(listener.emit())

if __name__ == '__main__':
    main()
