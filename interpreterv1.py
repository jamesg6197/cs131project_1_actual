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
        if s == InterpreterBase.TRUE_DEF:
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
            if class_name in self.classes:
                super().error(ErrorType.TYPE_ERROR)
            for item in class_def:
                if item[0] == InterpreterBase.FIELD_DEF:
                    name, value = item[1:]
                    if name in c_def.fields:
                        super().error(ErrorType.NAME_ERROR)
                    convert_success, value = convert_string_to_native_val(value)
                    if not convert_success:
                        super().error(ErrorType.TYPE_ERROR)
                    c_def.add_field(name, value)

                elif item[0] == InterpreterBase.METHOD_DEF:
                    name, parameters, statement = item[1:]
                    if name in c_def.methods:
                        super().error(ErrorType.NAME_ERROR)
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
    
    def convert_value(self, s, parameters = {}):
        if type(s) == Value or type(s) == ObjectDefinition:
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

    def __solve_expression(self, expression, parameters = {}):
        if type(expression) != list:
            return self.convert_value(expression, parameters)
        
        if len(expression) == 1:
            if type(expression[0]) == list:
                expression[0] = self.__solve_expression(expression[0])
            return self.convert_value(expression[0], parameters)
        
        elif len(expression) == 2:
            operator, op1 = expression
            
            if type(op1) == list:
                op1 = self.__solve_expression(op1)

            if operator == "!":
                op1 = self.convert_value(op1, parameters)
                if type(op1) != Value:
                    self.interpreter.error(ErrorType.TYPE_ERROR)
                if op1.type == bool:
                    return Value(str(not op1.get_pythonic_val()).lower(), bool)
                
            if operator == InterpreterBase.NEW_DEF:
                if op1 not in self.interpreter.classes:
                    self.interpreter.error(ErrorType.TYPE_ERROR)
                op1 = self.convert_value(op1, parameters)
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
            if type(op1) != ObjectDefinition:
                op1_py_val = op1.get_pythonic_val()
            if type(op2) != ObjectDefinition:
                op2_py_val = op2.get_pythonic_val()
            if (type(op1) == ObjectDefinition or type(op2) == ObjectDefinition) and operator not in ("==", "!="):
                self.interpreter.error(ErrorType.TYPE_ERROR, description = f'{operator} not supported between objects')

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
            elif operator  == "<":
                if (op1.type == int and op2.type == int) or \
                (op1.type == str and op2.type == str):
                    return Value(str(op1_py_val < op2_py_val).lower(), bool)
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
                if (type(op1) == ObjectDefinition and (type(op2) == Value and op2.type != None)):
                    self.interpreter.error(ErrorType.TYPE_ERROR)
                if (type(op2) == ObjectDefinition and (type(op1) == Value and op1.type != None)):
                    self.interpreter.error(ErrorType.TYPE_ERROR)
                if (type(op1) == ObjectDefinition and op2.type == None) or (type(op2) == ObjectDefinition and op1.type == None):
                    return Value(InterpreterBase.TRUE_DEF, bool)
                if (op1.type == op2.type):
                    return Value(str(op1_py_val != op2_py_val).lower(), bool)
                self.interpreter.error(ErrorType.TYPE_ERROR, description = f'!= operator not supported between {op1.type} and {op2.type}')
            elif operator == "==":
                if (type(op1) == ObjectDefinition and (type(op2) == Value and op2.type != None)):
                    self.interpreter.error(ErrorType.TYPE_ERROR)
                if (type(op2) == ObjectDefinition and (type(op1) == Value and op1.type != None)):
                    self.interpreter.error(ErrorType.TYPE_ERROR)
                if (type(op1) == ObjectDefinition and op2.type == None) or (type(op2) == ObjectDefinition and op1.type == None):
                    return Value(InterpreterBase.FALSE_DEF, bool)
                if (op1.type == op2.type):
                    return Value(str(op1_py_val == op2_py_val).lower(), bool)
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

    def __execute_print_statement(self, statement, parameters = {}):
        args = statement[1:]
        args = [self.__solve_expression(arg, parameters).val for arg in args]
        output = "".join(args)
        self.interpreter.output(output)
        return Value(str(InterpreterBase.NULL_DEF), None), False
    
    def __execute_set_statement(self, statement, parameters):
        _, var_name, var_val = statement
        var_val = self.__solve_expression(var_val, parameters)
        if var_name in parameters:
            parameters[var_name] = var_val
            return Value(str(InterpreterBase.NULL_DEF), None), False
        
        if var_name in self.fields:
            self.fields[var_name].value = var_val
            return Value(str(InterpreterBase.NULL_DEF), None), False
        
        self.interpreter.error(ErrorType.NAME_ERROR)


    def __execute_call_statement(self, statement, parameters = {}):
        _, obj, method, *method_params = statement
        method_params = [self.__solve_expression(param, parameters) for param in method_params]
        if obj == InterpreterBase.ME_DEF:
            if method not in self.methods:
                self.interpreter.error(ErrorType.NAME_ERROR)
            if len(method_params) != len(self.methods[method].parameters):
                self.interpreter.error(ErrorType.TYPE_ERROR)
            method_params = {self.methods[method].parameters[i]: self.convert_value(method_params[i], parameters) for i in range(len(method_params))}
            res = self.run_method(method, method_params)
            return res, False
        elif obj == InterpreterBase.NULL_DEF:
            self.interpreter.error(ErrorType.FAULT_ERROR)
        else:
            if type(obj) == list:
                obj = self.__solve_expression(obj, parameters)
                if type(obj) != ObjectDefinition:
                    self.interpreter.error(ErrorType.TYPE_ERROR)

            elif obj not in self.fields:
                self.interpreter.error(ErrorType.NAME_ERROR)

            else:
                obj = self.fields[obj].value
                if type(obj) != ObjectDefinition:
                    self.interpreter.error(ErrorType.FAULT_ERROR)


            if method not in obj.methods:
                self.interpreter.error(ErrorType.NAME_ERROR)

            if len(method_params) != len(obj.methods[method].parameters):
                self.interpreter.error(ErrorType.TYPE_ERROR)
            
            method_params = {obj.methods[method].parameters[i]: self.convert_value(method_params[i], parameters) for i in range(len(method_params))}
            res = obj.run_method(method, method_params)
            return res, False

    def __execute_all_sub_statements_of_begin_statement(self, statement, parameters = {}):
        sub_statements = statement[1:]
        exit_flag = False
        for substatement in sub_statements:
            res, exit_flag = self.__run_statement(substatement, parameters)
            if exit_flag:
                return res, exit_flag
        return res, exit_flag

    def __execute_return_statement(self, statement, parameters = {}):
        if len(statement) == 1:
            return Value(str(InterpreterBase.NULL_DEF), None), True
        _, expression = statement
    
        return_val = self.__solve_expression(expression, parameters)
        return return_val, True
    
    def __execute_if_statement(self, statement, parameters = {}):
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
            

    def __execute_while_statement(self, statement, parameters = {}):
        if len(statement) <= 2:
            self.interpreter.error(ErrorType.TYPE_ERROR)
        _, cond_exp, exp = statement

        cond_res = self.__solve_expression(cond_exp, parameters)
        if type(cond_res) != Value or cond_res.type != bool:
            self.interpreter.error(ErrorType.TYPE_ERROR)
        exit_flag = False
        res = Value(str(InterpreterBase.NULL_DEF), None)
        while cond_res.get_pythonic_val() == True and not exit_flag:
            res, exit_flag = self.__run_statement(exp, parameters)
            cond_res = self.__solve_expression(cond_exp, parameters)
            if exit_flag:
                return res, exit_flag
            if type(cond_res) != Value or cond_res.type != bool:
                self.interpreter.error(ErrorType.TYPE_ERROR)
        if type(cond_res) != Value or cond_res.type != bool:
                self.interpreter.error(ErrorType.TYPE_ERROR)
        return res, exit_flag


    def __execute_inputi_statement(self, statement, parameters = {}):
        _, input_field = statement
        user_input = self.interpreter.get_input()
        input_val = str(user_input)
        self.__execute_set_statement([InterpreterBase.SET_DEF, input_field, input_val], parameters)
        return Value(str(InterpreterBase.NULL_DEF), None), False

    def __execute_inputs_statement(self, statement, parameters = {}):
        _, input_field = statement
        user_input = self.interpreter.get_input()
        input_val = '"' + user_input + '"'
        self.__execute_set_statement([InterpreterBase.SET_DEF, input_field, input_val], parameters)
        return Value(str(InterpreterBase.NULL_DEF), None), False

    def __run_statement(self, statement, parameters = {}):
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
    
program_12 = [


	'(class main',
         '(method foo (q) ',
           '(while ((== null null))',
                    '(if (== (% q 3) 0)',
                        '(begin',
                            '(return)  # immediately terminates loop and function foo',
                            '(set q (- q 1))',
                        ')',
                    ')',
           ')  ',
         ')',
         '(method main () ',
           '(print (call me foo 5))',
         ')',
      ')',

]
##interpreter = Interpreter()
# # # interpreter.run(program_1) 
# # # print()
# # # interpreter.run(program_2) 
# # # print()
# # # interpreter.run(program_3)
# # # print()
# # # interpreter.run(program_4)
# # # print()
# # #interpreter.run(program_6)
# # # interpreter.run(program_7)
# # # print()
# # #interpreter.run(program_10)
# # #
#interpreter.run(program_12)