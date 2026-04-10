#!/usr/bin/env python3
"""
Example showing how to load a 32-bit immediate value in NervaPy.

For MOV.W lr, 0x11111111 equivalent, you have two options:

Option 1: Use MOVW + MOVT (more instructions, but no literal pool)
Option 2: Use LDR with literal pool (single instruction, requires literal pool)
"""

import sys
sys.path.insert(0, '/home/kris/repos/NervaPy')

from nervapy.arm import *
from nervapy.arm.abi import arm_gnueabihf
from nervapy.arm.microarchitecture import Microarchitecture
from nervapy.arm.literal_pool import Literal
from nervapy.arm.formats import AssemblyFormat
from nervapy.arm.generic import MOVW, MOVT

# Option 1: Using MOVW + MOVT
f = Function("load_using_movw", (), abi=arm_gnueabihf, target=Microarchitecture.CortexM4)
with f:
    # Load lower 16 bits with MOVW
    MOVW(lr, 0x1111)  # Sets lr = 0x00001111
    # Load upper 16 bits with MOVT
    MOVT(lr, 0x1111)  # Sets lr = 0x11111111
    BX(lr)

print("Option 1: Using MOVW + MOVT")
print(f.assembly)
print()

# Option 2: Using LDR with literal pool (recommended - single instruction)
f2 = Function("load_using_ldr", (), abi=arm_gnueabihf, target=Microarchitecture.CortexM4)
with f2:
    LDR(lr, literal=Literal(0x11111111, label="VALUE"))
    BX(lr)

print("Option 2: Using LDR with literal pool (recommended)")
print(f2.assembly)
