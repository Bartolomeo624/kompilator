import sys
from memory import MemoryManager


class BasicType(object):
    def __init__(self, lineno, _type=None, address=None):
        self.lineno = lineno
        self.type = _type
        self.address = address


class Int(BasicType):
    def __init__(self, lineno, is_iterator=False, address=None, _type="int"):
        self.is_iterator = is_iterator
        self.is_initialized = False if not is_iterator else True
        super().__init__(lineno, _type, address)


class Tab(BasicType):
    def __init__(self, lineno, start_index, end_index, address=None, _type="tab"):
        self.start_index = start_index
        self.end_index = end_index
        self.is_big = False
        if end_index - start_index < 1000:
            self.initialized_elements = {i: False for i in range(start_index, end_index + 1)}
        else:
            self.is_big = True
        super().__init__(lineno, _type, address)

    def is_initialized(self, index):
        if self.is_big:
            return True
        return self.initialized_elements[index]

    def initialize_element(self, index):
        if self.is_big:
            return
        self.initialized_elements[index] = True

    def initialize_all(self):
        if self.is_big:
            return
        for el in self.initialized_elements.keys():
            self.initialized_elements[el] = True

    def get_element_address(self, index):
        offset = index - self.start_index
        return self.address + offset


class VariableManager(object):
    def __init__(self):
        self.variables = {}
        self.shadowed ={}
        self.Memory = MemoryManager()
        self.error = False

    def __getitem__(self, var_name):
        try:
            return self.variables[var_name]
        except KeyError:
            raise KeyError("no such variable as {}".format(var_name))

    def new_variable(self, name, _type, line, start_index=None, end_index=None):
        if name in self.variables.keys():
            self.error = True
            original_var = self.variables[name]
            print("Error! line {}\n"
                  "Multiple declaration of a variable. {} already declared in {} line"
                  .format(line, name, original_var.lineno), file=sys.stderr)
        else:
            if _type == "int":
                address = self.Memory.allocate(1)
                self.variables[name] = Int(lineno=line, address=address)
            elif _type == "tab":
                tab_size = end_index - start_index + 1
                address = self.Memory.allocate(tab_size)
                self.variables[name] = Tab(lineno=line,
                                           start_index=start_index,
                                           end_index=end_index,
                                           address=address)

            else:
                raise ValueError("No variable type ", _type)

    def new_iterator(self, name, line):
        if name in self.variables.keys():
            self.shadowed[name] = self.variables[name]
            self.variables.__delitem__(name)
            # raise Warning("might be a problem")
        address = self.Memory.allocate_iterator()
        self.variables[name] = Int(lineno=line, address=address, is_iterator=True)
        # is initialized too

    def get_iterator_address(self, name):
        iterator = self.variables[name]
        if not iterator.is_iterator:
            raise Exception("U ARE PICKING NOT AN ITERATOR")
        return iterator.address

    def delete_iterator(self, name):
        iterator = self.variables[name]
        if not iterator.is_iterator:
            raise Exception("U ARE DELETING A VAR NOT ITER !!!")
        self.Memory.deallocate_iterator(iterator.address)
        self.variables.__delitem__(name)
        if name in self.shadowed.keys():
            self.variables[name] = self.shadowed[name]

    def check_if_in_bounds(self, tab_name, index, line):
        tab = self[tab_name]
        if index < tab.start_index or tab.end_index < index:
            self.error = True
            print("Error! line {}\n"
                  "Index {} is out of bounds for tab '{}'\n"
                  .format(line, index, tab_name), file=sys.stderr)
            return False
        return True

