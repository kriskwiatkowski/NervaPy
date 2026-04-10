from nervapy import *
from nervapy.arm import *
from nervapy.arm.microarchitecture import Microarchitecture
from nervapy.arm.abi import arm_gnueabi

with Function("test_overflow", (), target=Microarchitecture.CortexM33, abi=arm_gnueabi):
    # Create and USE 13 registers (which should exceed the limit)
    registers = [GeneralPurposeRegister() for _ in range(13)]

    # Use all of them so they're not dead code
    for i, reg in enumerate(registers):
        MOV(reg, i)

    # Make them all live by using them in a sum
    for i in range(1, len(registers)):
        ADD(registers[0], registers[0], registers[i])

    RETURN()

print("Test completed!")
