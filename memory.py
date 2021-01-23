class MemoryManager(object):
    """
    class imitating memory cells. address is an integer.
    """
    def __init__(self):
        # memory tab shows cells, that are already in use.
        self.memory = [1]  # some of the first values are reserved
        self.big_tab_bounds = []  # (123431, 991344) means that cells in 123431-991344 are reserved
        self.iterators_cells = 0
        # 1 reserved for printing a number value

    def check_big_tab_bounds(self, i):
        for bound in self.big_tab_bounds:
            lower = bound[0]
            upper = bound[1]
            if lower <= i <= upper:
                return False, upper
        return True, i

    def allocate(self, cells_number):
        if cells_number > 1000:
            address = self.memory[-1] + 1
            self.big_tab_bounds.append((address, address + cells_number))
            return address

        address = self.find_free_space(cells_number)
        index = self.memory.index(address - 1) + 1
        self.memory[index:index] = [i for i in range(address, address + cells_number)]
        return address
        # TODO: alloc tab differently !!! IMPORTANT

    def allocate_iterator(self):
        address = self.find_free_space(1, first_cell=2)
        index = self.memory.index(address - 1) + 1
        self.memory[index:index] = [address]
        return address

    def deallocate(self, cell, cells_number):
        # TODO: needs upgrade on ValueError behaviour, so it acts like a transaction.
        try:
            for c in range(cell, cell + cells_number):
                self.memory.remove(c)
        except ValueError:
            print("MemoryManager: can't deallocate a free cell")

    def deallocate_iterator(self, cell):
        try:
            self.memory.remove(cell)
        except ValueError:
            print("MemoryManager:iterator dealloc: can't deallocate a free cell")

    def find_free_space(self, cells_number, first_cell=None):
        """
        "looks for first available amount of space in memory where next n cells are free to take.
        "where n = cells_number
        :param cells_number: amount of space to find
        :param first_cell: starting from which cell start looking for space?
        :return: cell where the first of n elements can be saved.
        """
        starting_cell = self.iterators_cells + 3 if self.iterators_cells else 2
        is_free = False
        cell = starting_cell if not first_cell else first_cell
        while not is_free:
            is_free, cell = self._check_following_cells(cell, cells_number)
        return cell

    def _check_following_cells(self, i, rng):
        """
        checks if allocation in memory cells from i to i + rng - 1 is possible
        :param i: number of starting cell
        :param rng: range
        :return: tuple (Boolean, int) boolean tells if allocation is possible.
                 if possible, integer value shows cell number where you can allocate.
                 if not possible, integer value shows cell number where to continue searching.
        """
        outof_big_tab1, bound = self.check_big_tab_bounds(i)
        outof_big_tab2, bound2 = self.check_big_tab_bounds(i + rng)
        if not outof_big_tab1:
            return False, bound
        if not outof_big_tab2:
            return False, bound2

        for j in range(i, i + rng):
            if i == self.memory[-1]:
                return True, i + 1
            if j in self.memory:
                k = j + 1
                while k in self.memory:
                    k += 1
                return False, k  # can't allocate next rng cells starting from i
        return True, i  # next rng cells counting from i are free. allocation from cell i available


