from intbase import InterpreterBase, ErrorType
from bparser import BParser
from helpers import *
from typing import Union

def convert_string_to_native_val(s):
    if check_int(s): 
        return True, Value(str(int(s)), int)
    elif check_string(s):
        return True, Value(s[1:-1], str)
    elif check_bool(s):
        if s == 'true':
            return True, Value(InterpreterBase.TRUE_DEF, bool)
        return True, Value(InterpreterBase.FALSE_DEF, bool)
    elif check_null(s):
        return True, Value(InterpreterBase.NULL_DEF, None)
    else:
        return False, Value(str(None), None)
    
    
class Interpreter(InterpreterBase):
    def __init__(self, console_output=True, inp=None, trace_output=False):
        self.classes = {}
        super().__init__(console_output, inp)

    def run(self, program):
        result, parsed_program = BParser.parse(program)
        if result == False:
            return
        
        self.__discover_all_classes_and_track_them(parsed_program)
        class_def = self.__find_definition_for_class(InterpreterBase.MAIN_CLASS_DEF)
        obj = class_def.instantiate_object() 
        obj.run_method(InterpreterBase.MAIN_FUNC_DEF)

    def __find_definition_for_class(self, class_name):
        if class_name in self.classes:
            return self.classes[class_name]
        super().error(ErrorType.NAME_ERROR)

    def __discover_all_classes_and_track_them(self, parsed_program):
         for class_def in parsed_program:
            class_name = class_def[1] 
            c_def = ClassDefinition(class_name, self)
            for item in class_def:
                if item[0] == InterpreterBase.FIELD_DEF:
                    name, value = item[1:]
                    convert_success, value = convert_string_to_native_val(value)
                    if not convert_success:
                        super().error(ErrorType.TYPE_ERROR)
                    c_def.add_field(name, value)

                elif item[0] == InterpreterBase.METHOD_DEF:
                    name, parameters, statement = item[1:]
                    c_def.add_method(name, parameters, statement)

            self.classes[class_name] = c_def

class Value:
    def __init__(self, val, type):
        self.val = val
        self.type = type

    def get_pythonic_val(self):
        if self.type == int:
            return int(self.val)
        elif self.type == str:
            return self.val
        elif self.type == bool:
            if self.val == InterpreterBase.TRUE_DEF:
                return True
            return False
        elif self.type == None:
            return None
    
class Field:
    def __init__(self, name, value):
        self.name = name
        self.initial_value: Value = value
        self.value :  Union[Value, ObjectDefinition] = value

class Method:
    def __init__(self, name, parameters, statement):
        self.name = name
        self.parameters: list = parameters
        self.statement: list = statement

    def get_top_level_statement(self) -> list:
        return self.statement
    
    def get_params(self) -> list:
        return self.parameters


class ClassDefinition:
    def __init__(self, name, interpreter):
        self.interpreter = interpreter
        self.name = name
        self.methods = {}
        self.fields = {}

    def add_field(self, name, val):
        self.fields[name] = Field(name, val)

    def add_method(self, name,  statement, parameters = [],):
        self.methods[name] = Method(name, statement, parameters)

    def instantiate_object(self):
        obj = ObjectDefinition(self.interpreter)
        for method in self.methods.values():
            obj.add_method(method)
        for field in self.fields.values():
            obj.add_field(field)
        return obj

class ObjectDefinition:
    def __init__(self, interpreter: Interpreter):
        self.interpreter = interpreter
        self.fields = {}
        self.methods = {}

    def add_method(self, method: Method):
        self.methods[method.name] = method

    def add_field(self, field: Field):
        self.fields[field.name] = field

    def __find_method(self, method_name) -> Method:
        if method_name in self.methods:
            return self.methods[method_name]
        self.interpreter.error(ErrorType.NAME_ERROR)

    def run_method(self, method_name, parameters = {}):
        method = self.__find_method(method_name)
        statement = method.get_top_level_statement()
        result, _ = self.__run_statement(statement, parameters)
        return result
    
    def convert_value(self, s, parameters):
        if type(s) == Value:
            return s
        convert_success, value= convert_string_to_native_val(s) 
        if convert_success != False:
            return value
        if s in parameters:
            return parameters[s]
        if s in self.fields:
            return self.fields[s].value
        if s in self.interpreter.classes:
            return self.interpreter.classes[s]
        self.interpreter.error(ErrorType.NAME_ERROR, f'{s} is not defined')

    def __solve_expression(self, expression, parameters):
        if type(expression) != list:
            return self.convert_value(expression, parameters)
        
        if len(expression) == 1:
            return self.convert_value(expression[0], parameters)
        
        elif len(expression) == 2:
            operator, op1 = expression
            if type(op1) == list:
                op1 = self.__solve_expression(op1)

            op1 = self.convert_value(op1, parameters)
            if operator == "!":
                if type(op1) == bool:
                    return Value(str(not operator), bool)
                
            if operator == InterpreterBase.NEW_DEF:
                return op1.instantiate_object()
            
            
        elif expression[0] == InterpreterBase.CALL_DEF:
            res, _ = self.__execute_call_statement(expression, parameters)
            return res
        
        elif len(expression) == 3:
            operator, op1, op2 = expression
            if type(op1) == list:
                op1 = self.__solve_expression(op1, parameters)

            if type(op2) == list:
                op2 = self.__solve_expression(op2, parameters)
            op1 = self.convert_value(op1, parameters)
            op2 = self.convert_value(op2, parameters)
            op1_py_val, op2_py_val = op1.get_pythonic_val(), op2.get_pythonic_val()
            
            if operator == "+":
                if (op1.type == int and op2.type == int):
                    return Value(str(op1_py_val + op2_py_val), int)
                elif (op1.type == str and op2.type == str):
                    return Value(str(op1_py_val + op2_py_val), str)
                self.interpreter.error(ErrorType.TYPE_ERROR, description = f'+ operator not supported between {op1.type} and {op2.type}')
            elif operator == "-":
                if (op1.type == int and op2.type == int):
                    return Value(str(op1_py_val - op2_py_val), int)
                self.interpreter.error(ErrorType.TYPE_ERROR, description = f'- operator not supported between {op1.type} and {op2.type}')
            elif operator == "*":
                if (op1.type == int and op2.type == int):
                    return Value(str(op1_py_val * op2_py_val), int)
                self.interpreter.error(ErrorType.TYPE_ERROR, description = f'* operator not supported between {op1.type} and {op2.type}')

            elif operator == "/":
                if (op1.type == int and op2.type == int):
                    return Value(str(int(op1_py_val / op2_py_val)), int)
                self.interpreter.error(ErrorType.TYPE_ERROR, description = f'/ operator not supported between {op1.type} and {op2.type}')
            elif operator == "%":
                if (op1.type == int and op2.type == int):
                    return Value(str(op1_py_val % op2_py_val), int)
                self.interpreter.error(ErrorType.TYPE_ERROR, description = f'% operator not supported between {op1.type} and {op2.type}')
            elif operator  == ">":
                if (op1.type == int and op2.type == int) or \
                (op1.type == str and op2.type == str):
                    return Value(str(op1_py_val > op2_py_val).lower(), bool)
                self.interpreter.error(ErrorType.TYPE_ERROR, description = f'> operator not supported between {op1.type} and {op2.type}')
            elif operator == "<=":
                if (op1.type == int and op2.type == int) or \
                (op1.type == str and op2.type == str):
                    return Value(str(op1_py_val <= op2_py_val).lower(), bool)
                self.interpreter.error(ErrorType.TYPE_ERROR, description = f'<= operator not supported between {op1.type} and {op2.type}')
            elif operator == ">=":
                if (op1.type == int and op2.type == int) or \
                (op1.type == str and op2.type == str):
                    return Value(str(op1_py_val >= op2_py_val).lower(), bool)
                self.interpreter.error(ErrorType.TYPE_ERROR, description = f'>= operator not supported between {op1.type} and {op2.type}')
            elif operator == "!=":
                if (op1.type == int and op2.type == int) or \
                (op1.type == str and op2.type == str) or \
                (op1.type == bool and op2.type == bool):
                    return Value(str(op1_py_val != op2_py_val).lower(), bool)
                if (op1.type == None and op2.type == None):
                    return Value(InterpreterBase.FALSE_DEF, bool)
                if (op1.type == None or op2.type == None):
                    return Value(InterpreterBase.TRUE_DEF, bool)
                    
                
                self.interpreter.error(ErrorType.TYPE_ERROR, description = f'!= operator not supported between {op1.type} and {op2.type}')
            elif operator == "==":
                if (op1.type == int and op2.type == int) or \
                (op1.type == str and op2.type == str) or \
                (op1.type == bool and op2.type == bool):
                    return Value(str(op1_py_val == op2_py_val).lower(), bool)
                if (op1.type == None and op2.type == None):
                    return Value(InterpreterBase.TRUE_DEF, bool)
                elif (op1.type == None or op2.type == None):
                    return Value(InterpreterBase.FALSE_DEF, bool)
                self.interpreter.error(ErrorType.TYPE_ERROR, description = f'== operator not supported between {op1.type} and {op2.type}')
            elif operator == "&":
                if (op1.type == bool and op2.type == bool):
                    return Value(str(op1_py_val & op2_py_val).lower(), bool)
                self.interpreter.error(ErrorType.TYPE_ERROR, description = f'& operator not supported between {op1.type} and {op2.type}')
            elif operator == "|":
                if (op1.type == bool and op2.type == bool):
                    return Value(str(op1_py_val | op2_py_val).lower(), bool)
                self.interpreter.error(ErrorType.TYPE_ERROR, description = f'| operator not supported between {op1.type} and {op2.type}')
        self.interpreter.error(ErrorType.TYPE_ERROR)

    def __execute_print_statement(self, statement, parameters):
        args = statement[1:]
        args = [str(self.__solve_expression(arg, parameters).get_pythonic_val()) for arg in args]
        output = "".join(args)
        self.interpreter.output(output)
        return Value(str(InterpreterBase.NULL_DEF), None), False
    
    def __execute_set_statement(self, statement, parameters):
        _, var_name, var_val = statement
        var_val = self.__solve_expression(var_val, parameters)
        if var_name in parameters:
            parameters[var_name] = var_val
            return Value(str(InterpreterBase.NULL_DEF), None), False
        
        elif var_name in self.fields:
            self.fields[var_name].value = var_val
            return Value(str(InterpreterBase.NULL_DEF), None), False
        
        self.interpreter.error(ErrorType.NAME_ERROR)


    def __execute_call_statement(self, statement, parameters):
        _, obj, method, *method_params = statement
        method_params = [self.__solve_expression(param, parameters) for param in method_params]
        if obj == InterpreterBase.ME_DEF:
            if len(method_params) != len(self.methods[method].parameters):
                self.interpreter.error(ErrorType.TYPE_ERROR)
            method_params = {self.methods[method].parameters[i]: self.convert_value(method_params[i], parameters) for i in range(len(method_params))}
            res = self.run_method(method, method_params)
            return res, False

        else:
            if obj not in self.fields:
                self.interpreter.error(ErrorType.NAME_ERROR)

            obj = self.fields[obj].value
            if method not in obj.methods:
                self.interpreter.error(ErrorType.NAME_ERROR)

            if len(method_params) != len(obj.methods[method].parameters):
                self.interpreter.error(ErrorType.TYPE_ERROR)
            
            method_params = {obj.methods[method].parameters[i]: self.convert_value(method_params[i], parameters) for i in range(len(method_params))}
            res = obj.run_method(method, method_params)
            return res, False

    def __execute_all_sub_statements_of_begin_statement(self, statement, parameters):
        sub_statements = statement[1:]
        exit_flag = False
        for substatement in sub_statements:
            res, exit_flag = self.__run_statement(substatement, parameters)
            if exit_flag:
                return res, exit_flag
        return res, exit_flag

    def __execute_return_statement(self, statement, parameters):
        _, expression = statement
        return_val = self.__solve_expression(expression, parameters)
        return return_val, True
    
    def __execute_if_statement(self, statement, parameters):
        _, cond_exp, true_exp, *false_exp, = statement
        cond_res = self.__solve_expression(cond_exp, parameters)
        if type(cond_res) != Value or cond_res.type != bool:
            self.interpreter.error(ErrorType.TYPE_ERROR)
        exit_flag = False
        if cond_res.get_pythonic_val() == True:
            res, exit_flag = self.__run_statement(true_exp, parameters)
            return res, exit_flag
        else:
            if false_exp != []:
                res, exit_flag = self.__run_statement(false_exp[0], parameters)
                return res, exit_flag
            return Value(InterpreterBase.NULL_DEF, None), exit_flag
            

    def __execute_while_statement(self, statement, parameters):
        _, cond_exp, exp = statement
        
        cond_res = self.__solve_expression(cond_exp, parameters)
        if type(cond_res) != Value or cond_res.type != bool:
            self.interpreter.error(ErrorType.TYPE_ERROR)
        exit_flag = False
        while cond_res.get_pythonic_val() == True and not exit_flag:
            res, exit_flag = self.__run_statement(exp, parameters)
            cond_res = self.__solve_expression(cond_exp, parameters)
            if exit_flag:
                return res, exit_flag
        return res, exit_flag


    def __execute_inputi_statement(self, statement, parameters):
        _, input_field = statement
        user_input = self.interpreter.get_input()
        input_val = str(user_input)
        self.__execute_set_statement([InterpreterBase.SET_DEF, input_field, input_val], parameters)
        return Value(str(InterpreterBase.NULL_DEF), None), False

    def __execute_inputs_statement(self, statement, parameters):
        _, input_field = statement
        user_input = self.interpreter.get_input()
        input_val = '"' + user_input + '"'
        self.__execute_set_statement([InterpreterBase.SET_DEF, input_field, input_val], parameters)
        return Value(str(InterpreterBase.NULL_DEF), None), False

    def __run_statement(self, statement, parameters):
        result = Value(str(InterpreterBase.NULL_DEF), None)
        if is_a_print_statement(statement):
            result, exit_flag = self.__execute_print_statement(statement, parameters)
        elif is_an_inputi_statement(statement):
            result, exit_flag = self.__execute_inputi_statement(statement, parameters)
        elif is_an_inputs_statement(statement):
            result, exit_flag = self.__execute_inputs_statement(statement, parameters)
        elif is_a_set_statement(statement):
            result, exit_flag = self.__execute_set_statement(statement, parameters)
        elif is_a_call_statement(statement):
            result, exit_flag = self.__execute_call_statement(statement, parameters)
        elif is_a_while_statement(statement):
            result, exit_flag = self.__execute_while_statement(statement, parameters)
        elif is_an_if_statement(statement):
            result, exit_flag = self.__execute_if_statement(statement, parameters)
        elif is_a_return_statement(statement):
            result, exit_flag = self.__execute_return_statement(statement, parameters)
        elif is_a_begin_statement(statement):
            result, exit_flag = self.__execute_all_sub_statements_of_begin_statement(statement, parameters)
        return result, exit_flag


program_1 = ['(class main',
                    ' (field x 2)'
                    ' (field y "6")'
                    ' (method helloworld ()',
                    '   (begin',
                    '       (print "My boy")',
                    '       (set y "final value")',
                    '   )',
                    ')',
                    ' (method main ()',
                    '   (begin',
                    '       (print "hello")',
                    '       (set x 69)',
                    '       (set y "food!")',
                    '       (print "hello world!" 7 (+ x 69))',
                    '       (print (+ y " niawoid"))',
                    '       (call me helloworld)'
                    '       (print y)',
                    '   )',
                    ' ) # end of method',
                    ') # end of class']

program_2 = ['(class main',
                '(field other null)',
                '(field result 0)',
                '(method main ()',
                    '(begin',
                        '(call me foo 10 20)   # call foo method in same object',
                        '(set other (new other_class))',
                        '(call other foo 5 6)  # call foo method in other object',
                        '(print "square: " (call other square 10)) # call expression',
                        ')',
                    ')',
                '(method foo (a b)',
                    '(print a b)',
                ')',
                ')',
            '(class other_class',
                    '(method foo (q r) (print q r))',
                    '(method square (q) (return (* q q)))',
                ')',
            ]

program_3 = ['(class main',
                '(field x 0)',
                '(method main ()',
                    '(begin',
                        '(set x 7)	# input value from user, store in x variable',
                        '(if (== 0 (% x 2))',
                            '(print "x is even")',
                            '(print "x is odd")   # else clause',
                        ')',       
                        '(if (== x 7)',
                            '(print "lucky seven")  # no else clause in this version',
                        ')',  
                        '(if true (print "that\'s true") (print "this won\'t print"))',
                        ')',
                    ')',
                ')',]

program_4 = ['(class person',
                '(field name "")',
                '(field age 0)',
                '(method init (n a) (begin (set name n) (set age a)))',
                '(method talk (to_whom) (print name " says hello to " to_whom))',
                    ')',

            '(class main',
                '(field x 0)',
                '(method foo (q)',
                    '(begin',
                        '(set x 10)	 		# setting field to integer constant',
                        '(set q true)			# setting parameter to boolean constant', 
                        '(set x "foobar")		# setting field to a string constant',	 
                        '#(set x (* x 5))		 setting field to result of expression',
                        '(set x (new person))	# setting field to refer to new object',
                        '(set x null)			# setting field to null',
                        '(print x)',
                        ')',
                    ')',
                '(method main () ',
                    '(call me foo 5)',
                    ')',                
                ')',
            ]

program_5 = ['(class main',
                '(field x 0)',
                '(method main () ',
                    '(begin',
                        '(inputi x)',	 
                        '(while (> x 0) ',
                            '(begin',
                                '(print "x is " x)',
                                '(set x (- x 1))',
                                ')',
                            ')',          
                        ')',
                    ')',
                ')',
            ]

program_6 = ['(class main',
                '# private member fields',
                '(field num 0)',
                '(field result 1)',

                '# public methods',
                '(method main ()',
                    '(begin',
                        '(print "Enter a number: ")',
                        '(inputi num)',
                        '(print num " factorial is " (call me factorial num))',
                        ')',
                    ')',
                '(method factorial (n)',
                    '(begin',
                        '(set result 1)',
                        '(while (> n 0)',
                            '(begin',
                                '(set result (* n result))',
                                '(set n (- n 1))',
                                ')',
                            ')',
                        '(return result)',
                        ')',
                    ')'
                ')']

program_7 = ['(class main',
 '(field x 0)',
 '(field y "test")',
 '(method main ()',
  '(begin',
   '(inputi x)',
   '(print x)',
   '(inputi y)',
   '(print y)',
  ')',
 ')',
')',]
program_8 = ['(class main',
  '(method fact (n)',
   '(if (== n 1)',
     '(begin',
        '(return 1)',
        '(print "this should not be printed")'
        '(return 1)',
     ')',
     '(return (* n (call me fact (- n 1))))',
   ')',
  ')',
  '(method main () (print (call me fact 5)))',
')',]

program_9 = ['(class person',
   '(field name "")',
   '(field age 0)',
   '(method init (n a) (begin (set name n) (set age a)))',
   '(method talk (to_whom) (print name " says hello to " to_whom))',
   '(method get_age () (return age))',
')',
'(class main',
 '(field p null)',
 '(method tell_joke (to_whom) (print "Hey " to_whom ", knock knock!"))',
 '(method main ()',
   '(begin',
      '(call me tell_joke "Leia")  # calling method in the current obj',
      '(set p (new person))    ',
      '(call p init "Siddarth" 25)  # calling method in other object',
      '(call p talk "Boyan")        # calling method in other object',
      '(print "Siddarth\'s age is " (call p get_age))',
   ')',
 ')',
')',
]



program_10 = ['(class person',
         '(field name "")',
         '(field age 0)',
         '(method init (n a)',
            '(begin',
              '(set name n)',
              '(set age a)',
            ')',
         ')',
         
         '(method talk (to_whom)',
            '(print name " says hello to " to_whom)',
         ')',
      ')',

'(class main',
 '(field p null)',
 '(method tell_joke (to_whom)',
    '(print "Hey " to_whom ", knock knock!")',
 ')',
 '(method main ()',
   '(begin',
      '(call me tell_joke "Matt") # call tell_joke in current object',
      '(set p (new person))  # allocate a new person obj, point p at it',
      '(call p init "Siddarth" 25) # call init in object pointed to by p',
      '(call p talk "Paul")       # call talk in object pointed to by p',
      '(print (null))',
   ')',
 ')',
')',
]
program_11 = [
    '(class main',
    '(method main ()',
        '(if (!= 1 null)',
            '(print "hello")',
            ')',
        ')',
    ')',
]
interpreter = Interpreter()
# interpreter.run(program_1) 
# print()
# interpreter.run(program_2) 
# print()
# interpreter.run(program_3)
# print()
# interpreter.run(program_4)
# print()
#interpreter.run(program_6)
# interpreter.run(program_7)
# print()
#interpreter.run(program_10)
interpreter.run(program_10)
