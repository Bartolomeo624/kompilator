import sys

from sly import Parser
from lex import _Lexer


class _Parser(Parser):
    tokens = _Lexer.tokens

    def __init__(self):
        self.variables = []

    @_('DECLARE declarations BEGIN commands END')
    def program(self, p):
        return ("PROGRAM", p.declarations, p.commands)

    @_('BEGIN commands END')
    def program(self, p):
        return ("PROGRAM", [], p.commands)

    @_('declarations COMMA PIDENTIFIER LB NUM COL NUM RB')
    def declarations(self, p):
        if p.declarations is not None:
            self.variables.append(("tab", p[2], p[4], p[6], p.lineno))
            return p.declarations
        else:
            return

    @_('declarations COMMA PIDENTIFIER')
    def declarations(self, p):
        if p.declarations is not None:
            self.variables.append(("int", p[2], p.lineno))
            return p.declarations
        else:
            return

    @_('PIDENTIFIER LB NUM COL NUM RB')
    def declarations(self, p):
        self.variables.append(("tab", p[0], p[2], p[4], p.lineno))
        return self.variables

    @_('PIDENTIFIER')
    def declarations(self, p):
        self.variables.append(("int", p[0], p.lineno))
        return self.variables

    @_('')
    def declarations(self, p):
        return self.variables

    @_('commands command')
    def commands(self, p):
        cmds = p.commands
        cmds.append(p.command)
        return cmds

    @_('command')
    def commands(self, p):
        return [p.command]

    @_('identifier ASSIGN expression SEMICOL')
    def command(self, p):
        # if p[0][1] in [v[1] for v in self.variables]:
        return ("ASSIGN", p.identifier, p.expression, p.lineno)

    @_('IF condition THEN commands ELSE commands ENDIF')
    def command(self, p):
        return ("IF_ELSE", p.condition, p.commands0, p.commands1, p.lineno)

    @_('IF condition THEN commands ENDIF')
    def command(self, p):
        return ("IF", p.condition, p.commands, p.lineno)

    @_('WHILE condition DO commands ENDWHILE')
    def command(self, p):
        return ("WHILE", p.condition, p.commands, p.lineno)

    @_('REPEAT commands UNTIL condition SEMICOL')
    def command(self, p):
        return ("REPEAT", p.condition, p.commands, p.lineno)

    @_('FOR PIDENTIFIER FROM value TO value DO commands ENDFOR')
    def command(self, p):
        return ("FOR_TO", p[1], p.value0, p.value1, p.commands, p.lineno)

    @_('FOR PIDENTIFIER FROM value DOWNTO value DO commands ENDFOR')
    def command(self, p):
        return ("FOR_DT", p[1], p.value0, p.value1, p.commands, p.lineno)

    @_('READ identifier SEMICOL')
    def command(self, p):
        return ("READ", p.identifier, p.lineno)

    @_('WRITE value SEMICOL')
    def command(self, p):
        return ("WRITE", p.value, p.lineno)

    @_('value')
    def expression(self, p):
        return p.value

    @_('value ADD value', 'value SUB value',
       'value MUL value', 'value DIV value',
       'value MOD value')
    def expression(self, p):
        return (p[1], p.value0, p.value1, p.lineno)

    @_('value EQ value', 'value NEQ value',
       'value LT value', 'value GT value',
       'value LEQ value', 'value GEQ value')
    def condition(self, p):
        return (p[1], p.value0, p.value1, p.lineno)

    @_('NUM')
    def value(self, p):
        return ("NUM", p[0])

    @_('identifier')
    def value(self, p):
        return (p.identifier)

    @_('PIDENTIFIER')
    def identifier(self, p):
        return ("int", p[0], p.lineno)

    @_('PIDENTIFIER LB PIDENTIFIER RB')
    def identifier(self, p):
        # if p[2][0] == "int" and ('tab', p[2][1]) in [(v[0], v[1]) for v in self.variables]:
        #     print("Error! line {}\n"
        #           "Type of '{}' is 'tab'."
        #           " One can only refer to a single element of a table.\n"
        #           .format(p.lineno, p[2][1]), file=sys.stderr)
        #     raise KeyError
        return ("tab", p[0], ("int", p[2], p.lineno), p.lineno)

    @_('PIDENTIFIER LB NUM RB')
    def identifier(self, p):
        return ("tab", p[0], ("NUM", p[2]), p.lineno)


if __name__ == '__main__':
    lexer = _Lexer()
    parser = _Parser()
    text = open("test2.imp", "r")
    # print(type(text.read()))
    text = text.read()
    if text:
        for tok in lexer.tokenize(text):
            print(tok)
        #
        #
        # # parser.parse(lexer.tokenize(text))
        z = parser.parse(lexer.tokenize(text))
        print(z)
        print(parser.variables)
        # print(z[0])
        # print(z[1])
        # print(z[2])
        # print("\n")
