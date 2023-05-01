from intbase import InterpreterBase
def check_int(s):
    if s[0] in ('-', '+'):
        return s[1:].isdigit()
    return s.isdigit()

def check_string(s):
    if s[0] == '"' and s[-1] == '"':
        return True
    return False

def check_bool(s):
    return s == InterpreterBase.TRUE_DEF or s == InterpreterBase.FALSE_DEF
    
def check_null(s):
    return s == InterpreterBase.NULL_DEF

def is_a_print_statement(statement: list):
    return statement[0] == InterpreterBase.PRINT_DEF

def is_an_inputi_statement(statement: list):
    return statement[0] == InterpreterBase.INPUT_INT_DEF

def is_an_inputs_statement(statement:list):
    return statement[0] == InterpreterBase.INPUT_STRING_DEF

def is_a_call_statement(statement: list):
    return statement[0] == InterpreterBase.CALL_DEF

def is_a_while_statement(statement: list):
    return statement[0] == InterpreterBase.WHILE_DEF

def is_an_if_statement(statement: list):
    return statement[0] == InterpreterBase.IF_DEF

def is_a_return_statement(statement: list):
    return statement[0] == InterpreterBase.RETURN_DEF

def is_a_begin_statement(statement: list):
    return statement[0] == InterpreterBase.BEGIN_DEF

def is_a_set_statement(statement: list):
    return statement[0] == InterpreterBase.SET_DEF




        
        