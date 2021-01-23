def divide(module, divisor):
    temp = divisor
    while temp < module:
        temp *= 2


class MachineInstructions(object):
    def __init__(self):
        self.instructions = []
        self.labels_counter = 0

    def new_label(self):
        label = "LABEL" + str(self.labels_counter)
        self.labels_counter += 1
        return label

    def put_label(self, label):
        self.instructions.append(label)

    def remove_labels(self):
        labels = {}
        i = 0
        while len(self.instructions) > i:
            instr = self.instructions[i]
            if instr[0:5] == "LABEL":
                labels[instr] = i
                self.instructions.remove(instr)
            else:
                i += 1
        i = 0
        for instr in self.instructions:
            if 'LABEL' in instr:
                label = instr[instr.index("LABEL"):]
                offset = labels[label] - i
                self.instructions[i] = instr.replace(label, str(offset)).strip()
            i += 1

    def get(self, x, debug=""):
        x = x.lower()
        self.instructions.append("GET " + x + debug)

    def put(self, x):
        x = x.lower()
        self.instructions.append("PUT " + x)

    def load(self, x, y, debug=""):
        x = x.lower()
        y = y.lower()
        self.instructions.append("LOAD " + x + " " + y + debug)

    def store(self, x, y, debug=""):
        x = x.lower()
        y = y.lower()
        self.instructions.append("STORE " + x + " " + y + debug)

    def add(self, x, y):
        x = x.lower()
        y = y.lower()
        self.instructions.append("ADD " + x + " " + y)

    def sub(self, x, y):
        x = x.lower()
        y = y.lower()
        self.instructions.append("SUB " + x + " " + y)

    def reset(self, x, debug=""):
        x = x.lower()
        self.instructions.append("RESET " + x + debug)

    def inc(self, x):
        x = x.lower()
        self.instructions.append("INC " + x)

    def dec(self, x):
        x = x.lower()
        self.instructions.append("DEC " + x)

    def shr(self, x):
        """
        x <- x/2
        :param x: register name
        :return:
        """
        x = x.lower()
        self.instructions.append("SHR " + x)

    def shl(self, x):
        """
        x <- x*2
        :param x: register name
        :return:
        """
        x = x.lower()
        self.instructions.append("SHL " + x)

    def jump(self, j):
        self.instructions.append("JUMP " + j)

    def jzero(self, x, j):
        x = x.lower()
        self.instructions.append("JZERO " + x + " " + j)

    def jodd(self, x, j):
        x = x.lower()
        self.instructions.append("JODD " + x + " " + j)

    def halt(self):
        self.instructions.append("HALT")

    def generate_out_code(self):
        output_code = ""
        for inst in self.instructions:
            output_code += inst + "\n"
        return output_code
