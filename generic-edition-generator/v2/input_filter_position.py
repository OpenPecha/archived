import re
from typing import Pattern
from input_filter import InputFilter

class PositionInputFilter(InputFilter):

    """
    Very basic filter extracting a substring from the original
    """

    def __init__(self, arg, start: int, end: int = None):
        super().__init__(arg)
        assert(start >= 0)
        assert(end is None or end >= start)
        self.start = start
        self.end = end

    def correct(self, current_position):
        """
        this filter is so simple that we can optimize the correct function
        """
        return current_position + self.start

    def get_string(self):
        # we don't even need to add the position diff, but just in case
        self.add_position_diff(0, self.start)
        orig = self.get_arg_string()
        if self.end:
            return orig[self.start:self.end]
        return orig[self.start:]

