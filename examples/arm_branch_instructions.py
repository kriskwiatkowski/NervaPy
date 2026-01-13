#!/usr/bin/env python3
"""
Example: ARMv7-M Branch Instructions
====================================

This example demonstrates all ARMv7-M branch instructions available in NervaPy.
"""

from nervapy.arm.registers import r0, r1, r2, r3, lr
from nervapy.arm.generic import B, BLO, BX, BL, BLX, BEQ, BNE, CMP
from nervapy.arm.pseudo import Label
import nervapy.arm.function
import nervapy.stream


# Setup mock context
class MockFunction:
    collect_origin = False

nervapy.arm.function.active_function = MockFunction()
nervapy.stream.active_stream = None


def example_unconditional_branches():
    """
    Demonstrate unconditional branch instructions.
    """
    print("\n1. Unconditional Branch Instructions")
    print("=" * 60)
    
    # B - Branch to label
    loop_label = Label("main_loop")
    inst1 = B(loop_label)
    print(f"B (branch):          {str(inst1):30s} # Jump to label")
    
    # BL - Branch with Link (function call)
    func_label = Label("my_function")
    inst2 = BL(func_label)
    print(f"BL (call):           {str(inst2):30s} # Call function, saves return address in LR")
    
    # BX - Branch and Exchange (register)
    inst3 = BX(lr)
    print(f"BX (return):         {str(inst3):30s} # Return from function (branch to LR)")
    
    # BLX - Branch with Link and Exchange (register)
    inst4 = BLX(r3)
    print(f"BLX (indirect call): {str(inst4):30s} # Call function pointer in r3")


def example_conditional_branches():
    """
    Demonstrate conditional branch instructions.
    """
    print("\n2. Conditional Branch Instructions")
    print("=" * 60)
    print("Note: These follow a comparison instruction")
    
    # Compare two registers
    inst_cmp = CMP(r0, r1)
    print(f"\nCMP r0, r1          {str(inst_cmp):30s} # Compare r0 and r1")
    
    # Branch if Equal
    equal_label = Label("is_equal")
    inst1 = BEQ(equal_label)
    print(f"BEQ (equal):         {str(inst1):30s} # Branch if r0 == r1")
    
    # Branch if Not Equal
    not_equal_label = Label("not_equal")
    inst2 = BNE(not_equal_label)
    print(f"BNE (not equal):     {str(inst2):30s} # Branch if r0 != r1")
    
    # Branch if Lower (unsigned)
    lower_label = Label("is_lower")
    inst3 = BLO(lower_label)
    print(f"BLO (lower):         {str(inst3):30s} # Branch if r0 < r1 (unsigned)")


def example_function_call_pattern():
    """
    Demonstrate typical function call patterns.
    """
    print("\n3. Function Call Patterns")
    print("=" * 60)
    
    print("\nDirect function call:")
    func_label = Label("compute_value")
    inst1 = BL(func_label)
    print(f"  {str(inst1):30s} # Call compute_value()")
    
    print("\nIndirect function call (function pointer):")
    inst2 = BLX(r2)
    print(f"  {str(inst2):30s} # Call function at address in r2")
    
    print("\nReturn from function:")
    inst3 = BX(lr)
    print(f"  {str(inst3):30s} # Return to caller")


def example_branch_register_options():
    """
    Show that BX and BLX can use any register.
    """
    print("\n4. BX/BLX with Different Registers")
    print("=" * 60)
    
    print("\nBX (Branch and Exchange) - can use any register:")
    for i, reg in enumerate([r0, r1, r2, r3, lr], 1):
        inst = BX(reg)
        print(f"  {str(inst):30s} # Branch to address in {reg}")
    
    print("\nBLX (Branch with Link and Exchange) - can use any register:")
    for i, reg in enumerate([r0, r1, r2, r3], 1):
        inst = BLX(reg)
        print(f"  {str(inst):30s} # Call function at address in {reg}")


def example_real_world_usage():
    """
    Show realistic usage patterns.
    """
    print("\n5. Real-World Usage Examples")
    print("=" * 60)
    
    print("\nExample A: Function with early return")
    print("  void process(int value) {")
    print("      if (value < 0) return;  // Early return")
    print("      // ... process value")
    print("  }")
    print("\nAssembly:")
    
    # Check if value < 0
    inst1 = CMP(r0, 0)
    print(f"    {str(inst1):25s} # Compare value with 0")
    
    # Branch if Less Than (signed)
    from nervapy.arm.generic import BLT
    exit_label = Label("early_exit")
    inst2 = BLT(exit_label)
    print(f"    {str(inst2):25s} # If value < 0, goto early_exit")
    
    print("    ... process value ...")
    
    # Early exit point
    inst3 = BX(lr)
    print(f"  early_exit:")
    print(f"    {str(inst3):25s} # Return")
    
    print("\nExample B: Function pointer callback")
    print("  typedef void (*callback_t)(int);")
    print("  void call_callback(callback_t cb, int arg) {")
    print("      cb(arg);")
    print("  }")
    print("\nAssembly:")
    print("    # r0 = callback function pointer")
    print("    # r1 = argument")
    inst1 = BLX(r0)
    print(f"    {str(inst1):25s} # Call callback function")
    inst2 = BX(lr)
    print(f"    {str(inst2):25s} # Return")


def print_instruction_summary():
    """
    Print a summary of all branch instructions.
    """
    print("\n" + "=" * 60)
    print("Branch Instruction Summary")
    print("=" * 60)
    print("""
Unconditional Branches:
  B <label>     - Branch to label
  BX <Rm>       - Branch to address in register Rm (typically LR for return)
  BL <label>    - Branch with Link to label (saves return address in LR)
  BLX <Rm>      - Branch with Link to address in register Rm

Conditional Branches (after CMP/TST/etc):
  BEQ <label>   - Branch if Equal (Z=1)
  BNE <label>   - Branch if Not Equal (Z=0)
  BLO <label>   - Branch if Lower (unsigned, C=0)
  BHS <label>   - Branch if Higher or Same (unsigned, C=1)
  BLT <label>   - Branch if Less Than (signed)
  BGE <label>   - Branch if Greater or Equal (signed)
  BGT <label>   - Branch if Greater Than (signed)
  BLE <label>   - Branch if Less or Equal (signed)
  BHI <label>   - Branch if Higher (unsigned)
  BLS <label>   - Branch if Lower or Same (unsigned)
  ... and more condition codes

Key Points:
  • BX is used for returns: BX(lr)
  • BL is used for direct function calls
  • BLX is used for indirect function calls (function pointers)
  • All conditional branches require a preceding comparison/test instruction
  • BX and BLX can use any general-purpose register
""")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ARMv7-M Branch Instructions Examples")
    print("=" * 60)
    
    example_unconditional_branches()
    example_conditional_branches()
    example_function_call_pattern()
    example_branch_register_options()
    example_real_world_usage()
    print_instruction_summary()
    
    print("\n✓ All examples completed successfully!")
