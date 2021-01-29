import sys

from registers import Register, RegisterManager
from machine_instructions import MachineInstructions
from variable_types import Int, Tab, VariableManager
from parser import _Parser
from lex import _Lexer


class Compiler(object):
    def __init__(self, ast, output):
        self.ast = ast
        self.output_file = output
        self.nesting = {}
        self.error = False
        self.Registers = RegisterManager()
        self.Variables = VariableManager()
        self.Instructions = MachineInstructions()
        self.operation = {
            'ASSIGN': self.assign,
            'WRITE': self.write,
            'READ': self.read,
            'IF': self.if_endif,
            'IF_ELSE': self.if_else_endif,
            'WHILE': self.while_loop,
            'REPEAT': self.repeat_until_loop,
            'FOR_TO': self.for_to_loop,
            'FOR_DT': self.for_downto_loop,
        }

    """
    BASIC COMPILER FUNCTIONS ######################################################################
    """

    def check_errors(self):
        return bool(self.error + self.Variables.error)

    def compile(self, ast):
        if ast is None:
            print("Syntax error", file=sys.stderr)
            self.error = True
        # PROGRAM token is redundant now

        # fetch declarations and instructions
        declarations = ast[1]
        ast_instructions = ast[2]

        self.run_preprocessor(ast_instructions)
        # handle declarations if there are any
        if declarations:
            self.make_declarations(declarations)
        if ast_instructions:
            self.make_instructions(ast_instructions)
        self.Instructions.halt()
        self.Instructions.remove_labels()
        if not self.check_errors():
            with open(self.output_file, 'w') as f:
                for instr in self.Instructions.instructions:
                    print(instr, file=f)

    def check_nesting(self, ast_instructions, nesting=0):
        for ast_instr in ast_instructions:
            instr_type = ast_instr[0]
            if instr_type in ['FOR_TO', 'FOR_DT']:
                nesting += 1
                nesting += self.check_nesting(ast_instr[4])
        return nesting

    def run_preprocessor(self, ast_instructions):
        for i, ast_instr in enumerate(ast_instructions):
            instr_type = ast_instr[0]
            if instr_type in ['FOR_TO', 'FOR_DT']:
                self.nesting[i] = self.check_nesting(ast_instr[4])
        if self.nesting:
            max_iterators = 2 * (1 + max([self.nesting[k] for k in self.nesting.keys()]))
            self.Variables.Memory.iterators_cells = max_iterators
            self.Variables.Memory.memory += [max_iterators + 2]

    """
    ITERATOR FUNCTIONS ############################################################################
    """

    def declare_iterator(self, name, ast_init_rvalue, line, register="A", buffer2="F"):
        """
        Creates new int iterator variable with given name. Checks if init value is valid. Generates
        instructions which store the iterator and its value. In the end the value of iterator
        remains in :register: and its address remains in :buffer2:.
        :param name: Name of given iterator
        :param ast_init_rvalue: AST tuple with initial value info for iterator
        :param line: line number
        :param register: register in which the init value will be stored
        :param buffer2: register in which the iterators address will be stored
        :return:
        """
        self.check_rvalue(ast_init_rvalue)
        self.Variables.new_iterator(name, line)
        iterator = self.Variables[name]
        if not iterator.is_iterator:
            raise Exception("NOT AN ITERATOR")
        address = self.Variables.get_iterator_address(name)
        self.store_value_in_reg(ast_init_rvalue, register=register, buffer=buffer2)
        self.generate_value(buffer2, address)
        self.Instructions.store(register, buffer2)  # iterator starting value remains in register

    def delete_iterator(self, name):
        """
        Undeclares iterator with given name
        :param name: iterator name
        :return:
        """
        self.Variables.delete_iterator(name)

    def make_declarations(self, declarations):
        """
        Declares variables from the beginning of the source code.
        :param declarations: list of tuples - AST fragment
        :return:
        """
        ints = []
        tabs = []
        # tabs_lengths = {}

        for d in declarations:
            var_type = d[0]

            if var_type == "int":
                ints.append(d)
            elif var_type == "tab":
                tabs.append(d)
                # tab_elements = int(d[3]) - int(d[2]) TODO: sorting
                # tabs_lengths[name] = tab_elements
                # if tabs:
                #     for tab in tabs:
                #         if tabs_lengths[tab[1]] >= tab_elements:
                #             index = tabs.index(tab) + 1
                #             tabs[index:index] = d
                # else:
                #     tabs += d
            else:
                raise Exception("No such type as ", var_type)

        for d in ints:
            name, line = d[1], int(d[-1])
            self.Variables.new_variable(name, "int", line)

        for t in tabs:
            name, line, start, end = t[1], int(t[-1]), int(t[2]), int(t[3])
            self.Variables.new_variable(name, "tab", line,
                                        start_index=start,
                                        end_index=end)

    def make_instructions(self, instructions):
        """
        Driver function which performs instructions.
        :param instructions: list of AST fragments with instructions. list of tuples.
        :return:
        """
        for inst_ast in instructions:
            inst_type = inst_ast[0]
            self.operation[inst_type](inst_ast)

    def copy_reg(self, register1, register2):
        """
        Copies value of register2 to register 1. It doesn't change value of register2.
        :param register1: target register.
        :param register2: source register.
        :return:
        """
        # reg1 <- reg2
        self.Instructions.reset(register1)
        self.Instructions.add(register1, register2)

    def generate_value(self, reg_name, value):
        """
        Generates number in given register according to its binary representation
        by left shifts and incrementation operations.
        :param reg_name: Capital letter A-F - register symbol
        :param value: Decimal value, which will be generated in a register
        :return:
        """
        self.Instructions.reset(reg_name, debug=" (generating {})".format(value))
        if value >= 1:
            self.Instructions.inc(reg_name)
            binary = bin(value)[3:]  # strip '0b' and first '1' - it's added already!
            for bit in binary:
                if bit == "1":
                    self.Instructions.shl(reg_name)
                    self.Instructions.inc(reg_name)
                else:  # if bit == "0"
                    self.Instructions.shl(reg_name)
        self.Registers.set_reg(reg_name, value)

    def assign(self, ast_node, buffer="B", buffer2="A", buffer3="F"):
        """
        Handles assigment in code. In the end - value of buffer is lvalue address and value of
        buffer2 is rvalue
        :param ast_node: ast tuple with assign info
        :param buffer:
        :param buffer2:
        :param buffer3:
        :return:
        """
        # unpack
        lvalue = ast_node[1]
        rvalue = ast_node[2]
        var_type = lvalue[0]
        var_name = lvalue[1]

        # check if left and right hand side are valid
        if not self.check_lvalue(lvalue) or not self.check_rvalue(rvalue):
            return
        else:
            lvalue = self.Variables[var_name]
            self.store_value_in_reg(rvalue, register=buffer2,
                                    buffer=buffer)  # rvalue value in buffer2
            # at this moment - RESERVED: C, FREE: A,B,D,E,F
            # handle lvalue and get its address
            if var_type == 'int':
                address = lvalue.address
                self.generate_value(buffer, address)
                lvalue.is_initialized = True
            elif var_type == 'tab':
                ast_lvalue = ast_node[1]
                self.load_tab_element_address(ast_lvalue, register=buffer, buffer=buffer3,
                                              initialization=True)
            self.Instructions.store(buffer2, buffer)

    def read(self, ast_node, buffer="B", buffer2="C"):
        var_ast = ast_node[1]
        var_type = var_ast[0]
        var_name = var_ast[1]
        if not self.check_lvalue(var_ast):
            return
        lvalue = self.Variables[var_name]

        if var_type == 'int':
            address = lvalue.address
            self.generate_value(buffer, address)
            lvalue.is_initialized = True
        elif var_type == 'tab':
            ast_lvalue = ast_node[1]
            self.load_tab_element_address(ast_lvalue, register=buffer, buffer=buffer2,
                                          initialization=True)
        self.Instructions.get(buffer)

    def write(self, ast_node, buffer="B", buffer2="C"):
        ast_value = ast_node[1]
        if not self.check_rvalue(ast_value):
            return

        value_type = ast_value[0]
        if value_type == "NUM":
            value = int(ast_value[1])
            self.generate_value(buffer, value)
            self.generate_value(buffer2, 1)
            self.Instructions.store(buffer, buffer2)
            self.Instructions.put(buffer2)
        elif value_type == "tab":
            self.load_tab_element_address(ast_value, register=buffer, buffer=buffer2)
            self.Instructions.put(buffer)
        elif value_type == "int":
            int_name = ast_value[1]
            rvalue = self.Variables[int_name]
            self.generate_value(buffer, rvalue.address)
            self.Instructions.put(buffer)
        else:  # + - / * %
            self.do_arithmetics(ast_node, register=buffer, buffer=buffer2)
            self.Instructions.put(buffer)

    def store_value_in_reg(self, ast_node, register="B", buffer="F"):
        """
        Checks value in ast_node and generates it in register, no matter whether it is number, int,
        tab value or arithmetic operation
        :param ast_node:
        :param register:
        :param buffer:
        :return:
        """
        if register == buffer:
            raise Exception("use two different registers")
        node_type = ast_node[0]
        if node_type == "NUM":
            value = int(ast_node[1])
            self.generate_value(register, value)
        elif node_type in ["+", "-", "*", "/", "%"]:
            self.do_arithmetics(ast_node, register=register, buffer=buffer)
        elif node_type == "int":
            var_name = ast_node[1]
            int_var = self.Variables[var_name]
            self.load_int(int_var, register)
        elif node_type == "tab":
            var_name = ast_node[1]
            index = ast_node[2]
            tab_var = self.Variables[var_name]
            self.load_tab(tab_var, index, register=register, buffer=buffer)

    def load_int(self, _int, register="A"):
        """
        loads int variable value to a given register
        :param _int:
        :param register:
        :return:
        """
        address = _int.address
        self.generate_value(register, address)
        self.Instructions.load(register, register)

    def load_tab(self, _tab, index_ast_node, register="A", buffer="F"):
        """
        loads tab value to a given register
        :param _tab:
        :param index_ast_node:
        :param register:
        :param buffer:
        :return:
        """
        index_type = index_ast_node[0]
        if index_type == "NUM":
            index = int(index_ast_node[1])
            element_address = _tab.get_element_address(index)
            self.generate_value(buffer, element_address)
            self.Instructions.load(register, buffer)
        elif index_type == "int":
            var_name = index_ast_node[1]
            _int = self.Variables[var_name]
            self.generate_value(buffer, _tab.start_index)  # store tab starting index in buffer
            self.load_int(_int, register)  # load and store int variable value in register ("A")
            self.Instructions.sub(register, buffer)  # "A" = index - start_index (offset)
            self.generate_value(buffer, _tab.address)  # "F" = address
            self.Instructions.add(buffer, register)  # "F" = address + offset (elem_addr)
            self.Instructions.load(register, buffer)  # "A" = load  from address elem_addr

    def load_tab_element_address(self, tab_ast_node, register="A", buffer="F",
                                 initialization=False):
        """
        loads tab's element address to a given register
        :param tab_ast_node:
        :param register:
        :param buffer:
        :param initialization:
        :return:
        """
        tab_name = tab_ast_node[1]
        _tab = self.Variables[tab_name]
        index_ast_node = tab_ast_node[2]
        index_type = index_ast_node[0]

        if not self.check_rvalue(index_ast_node):
            return

        if index_type == "NUM":
            index = int(index_ast_node[1])
            element_address = _tab.get_element_address(index)
            self.generate_value(register, element_address)
            if initialization:
                _tab.initialize_element(index)
        elif index_type == "int":
            var_name = index_ast_node[1]
            _int = self.Variables[var_name]
            self.generate_value(buffer, _tab.start_index)  # store tab starting index in buffer
            self.load_int(_int, register)  # load and store int variable value in register ("A")
            self.Instructions.sub(register, buffer)  # "A" = index - start_index (offset)
            self.generate_value(buffer, _tab.address)  # "F" = address
            self.Instructions.add(register, buffer)  # "F" = address + offset (elem_addr)

    # CONTROL FLOW

    def if_endif(self, ast_node, buffer1="B", buffer2="C", buffer3="D"):
        ast_condition, ast_operations = ast_node[1], ast_node[2]
        cond_var1, cond_var2 = ast_condition[1], ast_condition[2]
        if not self.check_rvalue(cond_var1) or not self.check_rvalue(cond_var2):
            return
        label1 = self.Instructions.new_label()
        self.store_value_in_reg(cond_var1, register=buffer1, buffer=buffer3)
        self.store_value_in_reg(cond_var2, register=buffer2, buffer=buffer3)
        self.check_condition(ast_condition, buffer1, buffer2, buffer3)
        self.Instructions.jzero(buffer1, label1)
        self.make_instructions(ast_operations)
        self.Instructions.put_label(label1)

    def if_else_endif(self, ast_node, buffer1="B", buffer2="C", buffer3="D"):
        ast_condition, ast_if_ops, ast_else_ops = ast_node[1], ast_node[2], ast_node[3]
        cond_var1, cond_var2 = ast_condition[1], ast_condition[2]
        if not self.check_rvalue(cond_var1) or not self.check_rvalue(cond_var2):
            return
        label1 = self.Instructions.new_label()
        label2 = self.Instructions.new_label()
        self.store_value_in_reg(cond_var1, register=buffer1, buffer=buffer3)
        self.store_value_in_reg(cond_var2, register=buffer2, buffer=buffer3)
        self.check_condition(ast_condition, buffer1, buffer2, buffer3)
        self.Instructions.jzero(buffer1, label1)
        self.make_instructions(ast_if_ops)
        self.Instructions.jump(label2)
        self.Instructions.put_label(label1)
        self.make_instructions(ast_else_ops)
        self.Instructions.put_label(label2)

    def while_loop(self, ast_node, buffer1="B", buffer2="C", buffer3="D"):
        ast_condition, ast_operations = ast_node[1], ast_node[2]
        cond_var1, cond_var2 = ast_condition[1], ast_condition[2]
        if not self.check_rvalue(cond_var1) or not self.check_rvalue(cond_var2):
            return
        label1 = self.Instructions.new_label()
        label2 = self.Instructions.new_label()
        self.Instructions.put_label(label1)
        self.store_value_in_reg(cond_var1, register=buffer1, buffer=buffer3)
        self.store_value_in_reg(cond_var2, register=buffer2, buffer=buffer3)
        self.check_condition(ast_condition, buffer1, buffer2, buffer3)
        self.Instructions.jzero(buffer1, label2)
        self.make_instructions(ast_operations)
        self.Instructions.jump(label1)
        self.Instructions.put_label(label2)

    def repeat_until_loop(self, ast_node, buffer1="B", buffer2="C", buffer3="D"):
        ast_condition, ast_operations = ast_node[1], ast_node[2]
        cond_var1, cond_var2 = ast_condition[1], ast_condition[2]
        if not self.check_rvalue(cond_var1) or not self.check_rvalue(cond_var2):
            return
        label1 = self.Instructions.new_label()
        label2 = self.Instructions.new_label()
        self.Instructions.put_label(label1)
        self.make_instructions(ast_operations)
        self.store_value_in_reg(cond_var1, register=buffer1, buffer=buffer3)
        self.store_value_in_reg(cond_var2, register=buffer2, buffer=buffer3)
        self.check_condition(ast_condition, buffer1, buffer2, buffer3)
        self.Instructions.jzero(buffer1, label1)

    def for_to_loop(self, ast_node, buffer1="B", buffer2="C", buffer3="D"):
        list_ast_operations, iterator_name = ast_node[4], ast_node[1]
        ast_init_value, ast_to_value, line = ast_node[2], ast_node[3], ast_node[-1]
        label1 = self.Instructions.new_label()
        label2 = self.Instructions.new_label()
        endfor_name = iterator_name + "TO"
        self.declare_iterator(endfor_name, ast_to_value, line, register=buffer2, buffer2=buffer3)
        self.declare_iterator(iterator_name, ast_init_value, line, register=buffer1,
                              buffer2=buffer3)
        endfor = self.Variables[endfor_name]
        self.Instructions.put_label(label1)
        self.leq(register1=buffer1, register2=buffer2)
        self.Instructions.jzero(buffer1, label2)

        self.make_instructions(list_ast_operations)

        self.generate_value(buffer3, self.Variables.get_iterator_address(iterator_name))
        self.Instructions.load(buffer1, buffer3)
        self.Instructions.inc(buffer1)
        self.Instructions.store(buffer1, buffer3)
        self.load_int(endfor, buffer2)
        self.Instructions.jump(label1)
        self.Instructions.put_label(label2)
        self.delete_iterator(iterator_name)
        self.delete_iterator(endfor_name)

    def for_downto_loop(self, ast_node,
                        buffer1="B", buffer2="C", buffer3="D", buffer4="E", buffer5="F"):
        list_ast_operations, iterator_name = ast_node[4], ast_node[1]
        ast_init_value, ast_downto_value, line = ast_node[2], ast_node[3], ast_node[-1]
        label1 = self.Instructions.new_label()
        label2 = self.Instructions.new_label()
        label3 = self.Instructions.new_label()
        endfor_name = iterator_name + "DOWNTO"
        self.declare_iterator(endfor_name, ast_downto_value, line, register=buffer2,
                              buffer2=buffer3)
        self.declare_iterator(iterator_name, ast_init_value, line, register=buffer1,
                              buffer2=buffer3)
        endfor = self.Variables[endfor_name]

        self.copy_reg(buffer4, buffer1)  # buffer4 <- i = i - 1
        self.copy_reg(buffer5, buffer2)
        self.geq(register1=buffer4, register2=buffer5)
        self.Instructions.jzero(buffer4, label2)  # dont do the loop

        self.Instructions.put_label(label1)  # LOOP #################
        self.neq(buffer1, buffer2, buffer=buffer3)
        self.Instructions.jzero(buffer1, label3)  # last iteration ->>>> OUT OF LOOP

        self.make_instructions(list_ast_operations)

        self.generate_value(buffer3, self.Variables.get_iterator_address(iterator_name))
        self.Instructions.load(buffer1, buffer3)
        self.Instructions.dec(buffer1)
        self.Instructions.store(buffer1, buffer3)  # buffer1 <- i = i - 1
        self.load_int(endfor, buffer2)             # buffer2 <- endfor value
        # self.copy_reg(buffer4, buffer1)            # buffer4 <- i = i - 1
        # self.copy_reg(buffer5, buffer2)            # buffer5 <- endfor value
        self.Instructions.jump(label1)     # LOOP ################

        self.Instructions.put_label(label3)  # LAST ITER
        self.make_instructions(list_ast_operations)
        self.delete_iterator(iterator_name)
        self.delete_iterator(endfor_name)

        self.Instructions.put_label(label2)  # DONT DO THE LOOP

    def check_condition(self, ast_node, register1, register2, buffer="A"):
        condition = ast_node[0]
        if condition == '>':
            self.gt(register1, register2)
        elif condition == '<':
            self.lt(register1, register2)
        elif condition == '>=':
            self.geq(register1, register2)
        elif condition == '<=':
            self.leq(register1, register2)
        elif condition == '=':
            self.eq(register1, register2, buffer)
        elif condition == '!=':
            self.neq(register1, register2, buffer)
        else:
            print("No logical operator such as ", condition, file=sys.stderr)
            self.error = True

    def gt(self, register1, register2):
        self.Instructions.sub(register1, register2)

    def lt(self, register1, register2):
        self.Instructions.sub(register2, register1)
        self.copy_reg(register1, register2)

    def geq(self, register1, register2):
        self.Instructions.inc(register1)
        self.Instructions.sub(register1, register2)

    def leq(self, register1, register2):
        self.Instructions.inc(register2)
        self.Instructions.sub(register2, register1)
        self.copy_reg(register1, register2)

    def eq(self, register1, register2, buffer):
        # reg1 >= reg2 AND reg2 >= reg1 --> reg1 == reg2
        label1 = self.Instructions.new_label()
        self.copy_reg(buffer, register1)
        self.Instructions.inc(buffer)
        self.Instructions.sub(buffer, register2)  # check reg1 >= reg2
        # now if buffer =/= 0, then ok. Note that register1,2 stay unchanged
        self.Instructions.inc(register2)
        self.Instructions.sub(register2, register1)  # check reg2 >= reg1
        # now if register2 =/= 0, then ok. register2 value was changed
        self.Instructions.reset(register1)  # register1 <- 0
        # quit with reg1==0 if buffer==0 or register2==0
        self.Instructions.jzero(buffer, label1)
        self.Instructions.jzero(register2, label1)
        # if we are here, it means that reg1==reg2, so increase reg1 value
        self.Instructions.inc(register1)
        self.Instructions.put_label(label1)

    def neq(self, register1, register2, buffer):
        # if reg1 > reg2 OR reg 2 > reg 1
        self.copy_reg(buffer, register2)
        self.Instructions.sub(buffer, register1)  # r1 - r2, =0 if r1 <= r2
        self.Instructions.sub(register1, register2)  # r2 - r1, =0 if r1 >= r2
        self.Instructions.add(register1, buffer)  # sum be > 0 if r1 > r2 or r2 > r1

    def do_arithmetics(self, ast_node, register="B",
                       buffer="C", buffer1="D", buffer2="E", buffer3="F", buffer4="A"):
        operation = ast_node[0]
        if operation not in ["+", "-", "*", "/", "%"]:
            return  # TODO: print error

        if operation == "+":
            self.add(ast_node, register, buffer, buffer1)
        elif operation == "-":
            self.sub(ast_node, register, buffer, buffer1)
        elif operation == "*":
            self.mul(ast_node, register, buffer, buffer1)
        elif operation == "/":
            self.div(ast_node, register)  # buffer, buffer1, buffer2, buffer3)
        elif operation == "%":
            self.mod(ast_node, register)

    def add(self, ast_node, register="B", buffer="C", buffer2="D"):
        left_op = ast_node[1]
        right_op = ast_node[2]
        self.check_rvalue(left_op)
        self.check_rvalue(right_op)

        self.store_value_in_reg(left_op, register=register, buffer=buffer)
        self.store_value_in_reg(right_op, buffer, buffer=buffer2)
        self.Instructions.add(register, buffer)

    def sub(self, ast_node, register="B", buffer="C", buffer2="D"):
        left_op = ast_node[1]
        right_op = ast_node[2]
        self.check_rvalue(left_op)
        self.check_rvalue(right_op)

        self.store_value_in_reg(left_op, register=register, buffer=buffer)
        self.store_value_in_reg(right_op, buffer, buffer=buffer2)
        self.Instructions.sub(register, buffer)

    def mul(self, ast_node, register="B", buffer="C", buffer1="D"):
        left_op = ast_node[1]
        right_op = ast_node[2]
        self.check_rvalue(left_op)
        self.check_rvalue(right_op)

        if left_op[0] == right_op[0] == 'NUM' and int(left_op[1]) < int(right_op[1]):
            left_op, right_op = right_op, left_op

        label1 = self.Instructions.new_label()
        label2 = self.Instructions.new_label()
        label3 = self.Instructions.new_label()
        label4 = self.Instructions.new_label()
        self.store_value_in_reg(left_op, register=buffer, buffer=register)
        self.store_value_in_reg(right_op, register=buffer1, buffer=register)
        self.Instructions.reset(register)
        self.Instructions.put_label(label1)
        self.Instructions.jzero(buffer1, label4)
        self.Instructions.jodd(buffer1, label3)
        self.Instructions.put_label(label2)
        self.Instructions.shr(buffer1)
        self.Instructions.shl(buffer)
        self.Instructions.jump(label1)
        self.Instructions.put_label(label3)
        self.Instructions.add(register, buffer)
        self.Instructions.jump(label2)
        self.Instructions.put_label(label4)

    def div(self, ast_node, register="B",
            buffer="C", buffer1="D", buffer2="E", buffer3="F"):
        left_op = ast_node[1]
        right_op = ast_node[2]
        self.check_rvalue(left_op)
        self.check_rvalue(right_op)

        label1 = self.Instructions.new_label()
        label2 = self.Instructions.new_label()
        label3 = self.Instructions.new_label()
        label4 = self.Instructions.new_label()
        label5 = self.Instructions.new_label()
        # C         D       E       F
        module, divisor, counter, tmp = buffer, buffer1, buffer2, buffer3
        self.store_value_in_reg(left_op, module, buffer=tmp)
        self.store_value_in_reg(right_op, divisor, tmp)
        self.Instructions.reset(register)
        self.Instructions.jzero(divisor, label5)
        self.Instructions.reset(counter)
        self.Instructions.inc(counter)
        self.Instructions.put_label(label1)
        self.copy_reg(tmp, module)
        self.Instructions.inc(tmp)
        self.Instructions.sub(tmp, divisor)
        self.Instructions.jzero(tmp, label2)
        self.Instructions.shl(divisor)
        self.Instructions.shl(counter)
        self.Instructions.jump(label1)
        self.Instructions.put_label(label2)
        self.Instructions.jzero(counter, label4)
        self.copy_reg(tmp, module)
        self.Instructions.inc(tmp)
        self.Instructions.sub(tmp, divisor)
        self.Instructions.jzero(tmp, label3)
        self.Instructions.add(register, counter)
        self.Instructions.sub(module, divisor)
        self.Instructions.put_label(label3)
        self.Instructions.shr(counter)
        self.Instructions.shr(divisor)
        self.Instructions.jump(label2)
        self.Instructions.put_label(label5)
        self.Instructions.reset(module)
        self.Instructions.put_label(label4)

    def mod(self, ast_node, register="B",
            buffer="C", buffer1="D", buffer2="E", buffer3="F"):
        self.div(ast_node, register=buffer, buffer=register)

    def check_lvalue(self, var_info):
        """
        Checks if a thing described in ast var_info can be a variable, which can be updated.
        :param var_info:
        :return:
        """
        var_type = var_info[0]
        var_name = var_info[1]
        line = var_info[-1]

        try:
            lvalue = self.Variables[var_name]
        except KeyError:
            self.error = True
            print("Error! line {}\n"
                  "Variable '{}' was not declared\n"
                  .format(line, var_name), file=sys.stderr)
            return False

        if var_type == "tab":
            # unpack the rest
            index = var_info[2]
            index_type = index[0]

            if lvalue.type == "int":
                self.error = True
                print("Error! line {}\n"
                      "Type of '{}' is 'int'."
                      "Can't refer to an element od int.\n"
                      .format(line, var_name), file=sys.stderr)
                return False

            if index_type == "NUM":
                num = int(index[1])
                if not self.Variables.check_if_in_bounds(var_name, num, line):
                    return False
            elif index_type == "int":
                lvalue.initialize_all()
                int_name = index[1]
                try:
                    int_var = self.Variables[int_name]
                except KeyError:
                    self.error = True
                    print("Error! line {}\n"
                          "Variable '{}' was not declared\n"
                          .format(line, int_name), file=sys.stderr)
                    return False
                if not int_var.is_initialized:
                    self.error = True
                    print("Error! line {}\n"
                          "Variable '{}' was not initialized\n"
                          .format(line, int_name), file=sys.stderr)
                    return False

        elif var_type == "int":
            if lvalue.type == "tab":
                self.error = True
                print("Error! line {}\n"
                      "Type of '{}' is 'tab'."
                      " One can only refer to a single element of a table using tab(n).\n"
                      .format(line, var_name), file=sys.stderr)
                return False
            elif lvalue.is_iterator:
                self.error = True
                print("Error! line {}\n"
                      "{} is an iterator. "
                      "Cannot change iterator value inside a loop\n"
                      .format(line, var_name), file=sys.stderr)
        else:
            return False

        return True

    def check_rvalue(self, ast_node):
        """
        Checks if a thing described in ast_node is a existing valid value.
        :param ast_node:
        :return:
        """
        node_type = ast_node[0]
        line = ast_node[-1]
        if node_type == "NUM":
            return True
        elif node_type in ["+", "-", "*", "/", "%"]:
            left_op, right_op = ast_node[1], ast_node[2]
            return self.check_rvalue(left_op) and self.check_rvalue(right_op)
        elif node_type in ["tab", "int"]:
            var_type = node_type
            var_name = ast_node[1]

            try:
                var = self.Variables[var_name]
            except KeyError:
                self.error = True
                print("Error! line {}\n"
                      "Variable '{}' was not declared\n"
                      .format(line, var_name), file=sys.stderr)
                return False

            if var_type == "tab":
                index = ast_node[2]
                index_type = index[0]

                if index_type == "NUM":
                    num = int(index[1])
                    if not self.Variables.check_if_in_bounds(var_name, num, line):
                        return False
                    if not self.Variables[var_name].is_initialized(num):
                        self.error = True
                        print("Error! line {}\n"
                              "{} element of tab {} is not initialized\n"
                              .format(line, num, var_name), file=sys.stderr)

                elif index_type == "int":
                    int_name = index[1]
                    try:
                        int_var = self.Variables[int_name]
                    except KeyError:
                        self.error = True
                        print("Error! line {}\n"
                              "Variable '{}' was not declared\n"
                              .format(line, int_name), file=sys.stderr)
                        return False
                    if not int_var.is_initialized:
                        self.error = True
                        print("Error! line {}\n"
                              "Variable '{}' was not initialized\n"
                              .format(line, int_name), file=sys.stderr)
                        return False
            elif var_type == "int":
                if var.type == "tab":
                    self.error = True
                    print("Error! line {}\n"
                          "Type of '{}' is 'tab'."
                          " One can only refer to a single element of a table using tab(n).\n"
                          .format(line, var_name), file=sys.stderr)
                    return False
                elif not var.is_initialized:
                    self.error = True
                    print("Error! line {}\n"
                          "Variable '{}' was not initialized\n"
                          .format(line, var_name), file=sys.stderr)
                    return False
        return True


if __name__ == '__main__':
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    p = _Parser()
    l = _Lexer()
    text = open(input_file, "r")
    text = text.read()
    ast = p.parse(l.tokenize(text))
    if ast is not None:
        c = Compiler(ast, output_file)
        c.compile(ast)

