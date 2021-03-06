# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals

from arpeggio import Optional, ZeroOrMore, Not, OneOrMore, EOF, ParserPython, visit_parse_tree
from arpeggio import RegExMatch as _
from arpeggio.peg import PEGVisitor
from arpeggio.peg import ParserPEG as ParserPEGOrig


# Lexical invariants
ASSIGNMENT = "="
ORDERED_CHOICE = "/"
ZERO_OR_MORE = "*"
ONE_OR_MORE = "+"
OPTIONAL = "?"
UNORDERED_GROUP = "#"
AND = "&"
NOT = "!"
OPEN = "("
CLOSE = ")"

# PEG syntax rules
def peggrammar():       return OneOrMore(rule), EOF
def rule():             return rule_name, ASSIGNMENT, ordered_choice , ";"
def ordered_choice():   return sequence, ZeroOrMore(ORDERED_CHOICE, sequence)
def sequence():         return OneOrMore(prefix)
def prefix():           return Optional([AND, NOT]), sufix
def sufix():            return expression, Optional([OPTIONAL,
                                                     ZERO_OR_MORE,
                                                     ONE_OR_MORE,
                                                     UNORDERED_GROUP])
def expression():       return [regex, rule_crossref,
                                (OPEN, ordered_choice, CLOSE),
                                str_match], Not(ASSIGNMENT)

# PEG Lexical rules
def regex():            return [("r'", _(r'''[^'\\]*(?:\\.[^'\\]*)*'''), "'"),
                                ('r"', _(r'''[^"\\]*(?:\\.[^"\\]*)*'''), '"')]
def rule_name():        return _(r"[a-zA-Z_]([a-zA-Z_]|[0-9])*")
def rule_crossref():    return rule_name
def str_match():        return _(r'''(?s)('[^'\\]*(?:\\.[^'\\]*)*')|'''
                                 r'''("[^"\\]*(?:\\.[^"\\]*)*")''')
def comment():          return _("//.*\n")


class MyPEG(ParserPEGOrig):

    def _from_peg(self, language_def):
        self.root_rule_name = "CompilationUnit"

        parser = ParserPython(peggrammar, comment, reduce_tree=False,
                              debug=self.debug)
        parser.root_rule_name = self.root_rule_name
        parse_tree = parser.parse(language_def)
        #print(parse_tree)

        self.parser_model, self.comment_model = visit_parse_tree(parse_tree, PEGVisitor(self.root_rule_name,
                                                       self.comment_rule_name,
                                                       self.ignore_case,
                                                       debug=self.debug))
        return self.parser_model, self.comment_model

