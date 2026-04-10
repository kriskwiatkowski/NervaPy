#!/usr/bin/env python
"""
Example showing how to check live registers at any point in NervaPy code.

To check live registers:
1. Set report_live_registers=True when creating the Function
2. Access instruction.live_registers after the function context exits
3. Or use the debug helper below to print live registers during generation
"""

from nervapy import *
from nervapy.arm.function import active_function
from nervapy.arm.instructions import Instruction


def print_live_registers(label=""):
    """
    Print all live registers at the current point in code generation.
    
    Usage:
        with Function(..., report_live_registers=True):
            # ... some instructions
            print_live_registers("After first block")
            # ... more instructions
    """
    if active_function is None:
        print(f"{label}: No active function")
        return
    
    # Get the last instruction added
    if not active_function.instructions:
        print(f"{label}: No instructions yet")
        return
    
    last_instruction = active_function.instructions[-1]
    
    # Check if it's an actual instruction with live_registers
    if isinstance(last_instruction, Instruction):
        if hasattr(last_instruction, 'live_registers'):
            live_regs = sorted(map(str, list(last_instruction.live_registers)))
            print(f"{label}: Live registers = [{', '.join(live_regs)}]")
        else:
            print(f"{label}: Instruction has no live_registers attribute yet (determine_live_registers not called)")
    else:
        print(f"{label}: Last item is not an Instruction")


def is_register_live(register):
    """
    Check if a register is currently live.
    
    Args:
        register: The register to check (e.g., r0, r1, etc.)
    
    Returns:
        True if the register is live, False otherwise
    """
    if active_function is None:
        return False
    
    if not active_function.instructions:
        return False
    
    last_instruction = active_function.instructions[-1]
    
    if isinstance(last_instruction, Instruction) and hasattr(last_instruction, 'live_registers'):
        for live_reg in last_instruction.live_registers:
            if str(live_reg) == str(register):
                return True
    
    return False


# Example usage
if __name__ == "__main__":
    from nervapy.arm.abi import arm_gnueabi
    from nervapy.arm.formats import AssemblyFormat
    from nervapy.arm.function import Function
    from nervapy.arm.registers import GeneralPurposeRegister, r0
    from nervapy.arm.generic import MOV, ADD, MUL
    from nervapy.arm.microarchitecture import Microarchitecture
    
    # Create a simple function to demonstrate
    # Function that returns r0, so r0 will be live at the end
    with Function(
        "example_live_regs",
        [],
        target=Microarchitecture.CortexM33,
        abi=arm_gnueabi,
        assembly_format=AssemblyFormat.GAS,
        report_live_registers=True,  # IMPORTANT: Enable live register tracking
    ) as f:
        # Allocate some virtual registers
        r0_val = GeneralPurposeRegister()
        r1_val = GeneralPurposeRegister()
        r2_val = GeneralPurposeRegister()
        r3_val = GeneralPurposeRegister()
        r4_val = GeneralPurposeRegister()
        
        # Add some instructions
        MOV(r0_val, 42)
        MOV(r1_val, 100)
        ADD(r2_val, r0_val, r1_val)  # r0_val and r1_val are live before this
        MOV(r3_val, 200)
        MUL(r4_val, r2_val, r3_val)  # r2_val and r3_val are live before this
        
        # Return r4_val by moving it to r0
        MOV(r0, r4_val)  # r4_val is live before this, r0 is live after
        
    # Now we can inspect live registers for each instruction
    print("\nLive registers at each instruction:")
    print("=" * 60)
    for i, instr in enumerate(f.instructions):
        if isinstance(instr, Instruction):
            live_regs = sorted(map(str, list(instr.live_registers)))
            print(f"{i:3d}: {str(instr):40s} Live: [{', '.join(live_regs)}]")
    
    print("\n" + "=" * 60)
    print("\nGenerated assembly:")
    print(f.assembly)
