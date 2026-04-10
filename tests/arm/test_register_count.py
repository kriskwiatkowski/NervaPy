from nervapy import *
from nervapy.arm import *
from nervapy.arm.microarchitecture import Microarchitecture
from nervapy.arm.abi import arm_gnueabi

with Function("test_many_registers", (), target=Microarchitecture.CortexM4, abi=arm_gnueabi):
    # Create many registers but only use a few
    registers = [GeneralPurposeRegister() for _ in range(20)]
    
    # Only actually use the first 5 in operations
    MOV(registers[0], 1)
    MOV(registers[1], 2)
    ADD(registers[2], registers[0], registers[1])
    MOV(registers[3], registers[2])
    MOV(registers[4], registers[3])
    
    # The other 15 are dead code and should be eliminated
    RETURN()

print("Test completed successfully!")
