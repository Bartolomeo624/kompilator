from sly import Lexer


class _Lexer(Lexer):
    tokens = {PIDENTIFIER, NUM, DECLARE, BEGIN, END,
              IF, THEN, ELSE, ENDIF,
              WHILE, DO, ENDWHILE,
              REPEAT, UNTIL,
              FOR, FROM, TO, DOWNTO, ENDFOR,
              READ, WRITE, ASSIGN,
              EQ, NEQ, LT, GT, LEQ, GEQ,
              ADD, SUB, MUL, DIV, MOD,
              LB, RB,
              COL, SEMICOL, COMMA}

    ignore = ' \t'
    ignore_comment = r'\[[^\]]*\]'
    ignore_newline = r'\n'

    PIDENTIFIER = r'[_a-z]+'
    NUM = r'\d+'

    DECLARE = r'DECLARE'
    BEGIN = 'BEGIN'
    ENDWHILE = r'ENDWHILE'
    ENDFOR = r'ENDFOR'
    ENDIF = r'ENDIF'
    END = 'END'

    IF = r'IF'
    THEN = r'THEN'
    ELSE = r'ELSE'

    WHILE = r'WHILE'
    DOWNTO = r'DOWNTO'
    DO = r'DO'

    REPEAT = r'REPEAT'
    UNTIL = 'UNTIL'

    FOR = r'FOR'
    FROM = r'FROM'
    TO = r'TO'

    READ = r'READ'
    WRITE = r'WRITE'
    ASSIGN = r':='

    NEQ = r'!='
    LEQ = r'<='
    GEQ = r'>='
    EQ = r'='
    LT = r'<'
    GT = r'>'

    ADD = r'\+'
    SUB = r'\-'
    MUL = r'\*'
    DIV = r'\/'
    MOD = r'%'

    LB = r'\('
    RB = r'\)'

    COL = r':'
    SEMICOL = r';'
    COMMA = r','

    def ignore_comment(self, t):
        return

    def ignore_newline(self, t):
        self.lineno += 1

    def error(self, t):
        print("Błąd składni. Numer lini: ", self.lineno, t.value)
        self.index += 1