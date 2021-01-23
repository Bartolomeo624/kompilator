reg_names = "ABCDEF"


class Register(object):
    def __init__(self, name):
        self.name = name
        self.value = None
        self.is_free = True

    def __str__(self):
        return self.name


class RegisterManager(object):
    def __init__(self):
        self.registers = {x: Register(x) for x in reg_names}

    def __getitem__(self, register):
        return self.registers[register]

    def set_reg(self, name, value):
        reg = self[name]
        reg.value = value
        reg.is_free = False

    def free_reg(self, name):
        reg = self[name]
        reg.value = None
        reg.is_free = True
