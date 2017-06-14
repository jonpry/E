#!/bin/sh
java -cp /home/jon/antlr4/tool/target/antlr4-4.7.1-SNAPSHOT-complete.jar org.antlr.v4.Tool -Dlanguage=Python2 ANTLRv4Lexer.g4
java -cp /home/jon/antlr4/tool/target/antlr4-4.7.1-SNAPSHOT-complete.jar org.antlr.v4.Tool -Dlanguage=Python2 ANTLRv4Parser.g4
java -cp /home/jon/antlr4/tool/target/antlr4-4.7.1-SNAPSHOT-complete.jar org.antlr.v4.Tool -Dlanguage=Python2 Java.g4

