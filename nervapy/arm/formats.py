# This file is part of PeachPy package and is licensed under the Simplified BSD license.
#    See license.rst for the full text of the license.

from typing import Optional


class AssemblyFormat:
    """Defines different assembly output formats for ARM processors."""

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return self.name == other.name

    # Assembly format constants
    GAS: Optional["AssemblyFormat"] = None  # GNU Assembler (default)
    ARMCC: Optional["AssemblyFormat"] = None  # ARM Compiler armasm


class HighRegisterStrategy:
    """Defines strategies for handling high registers (r8-r15) in ARMv7-M."""

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return self.name == other.name

    # High register handling strategies
    PUSH_W: Optional["HighRegisterStrategy"] = None  # Use PUSH.W/POP.W for high registers (modern, efficient)
    STMDB: Optional["HighRegisterStrategy"] = None  # Use STMDB sp!/LDMIA sp! for high registers (compatible)
    AUTO: Optional["HighRegisterStrategy"] = None  # Automatically choose based on target and assembler


# Initialize format constants
AssemblyFormat.GAS = AssemblyFormat("GAS")
AssemblyFormat.ARMCC = AssemblyFormat("ARMCC")

# Initialize strategy constants
HighRegisterStrategy.PUSH_W = HighRegisterStrategy("PUSH_W")
HighRegisterStrategy.STMDB = HighRegisterStrategy("STMDB")
HighRegisterStrategy.AUTO = HighRegisterStrategy("AUTO")
