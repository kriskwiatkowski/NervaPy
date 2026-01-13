#!/usr/bin/env python3
"""
Example: Using LDR_W with Shifted Register Offsets
===================================================

This example demonstrates how to generate ARM load/store instructions with
shifted register offsets, such as: ldr.w r2, [r6, r5, lsl #2]

This addressing mode is useful for accessing array elements with different
element sizes.
"""

from nervapy.arm.registers import r0, r1, r2, r3, r4, r5, r6, ShiftedGeneralPurposeRegister
from nervapy.arm.generic import LDR_W, LDR, STR_W, STR, LDRH_W, STRH_W, LDRB_W, STRB_W
import nervapy.arm.function
import nervapy.stream


# Setup mock context for instruction generation (not using full Function API)
class MockFunction:
    collect_origin = False

nervapy.arm.function.active_function = MockFunction()
nervapy.stream.active_stream = None


def example_shifted_load_store():
    """
    Generate LDR/STR instructions with shifted register offsets.
    """
    print("\nExample 1: Various Shifted Load/Store Instructions")
    print("=" * 60)
    
    # Example 1: Access 32-bit array element
    # Equivalent to: array[index] where each element is 4 bytes
    # ldr.w r2, [r6, r5, lsl #2]
    index_shifted = ShiftedGeneralPurposeRegister(r5, 'LSL', 2)
    inst1 = LDR_W(r2, [r6, index_shifted])
    print(f"1. {str(inst1):40s} # Load word, index * 4")
    
    # Example 2: Store to 32-bit array
    # str.w r3, [r6, r5, lsl #2]
    inst2 = STR_W(r3, [r6, index_shifted])
    print(f"2. {str(inst2):40s} # Store word, index * 4")
    
    # Example 3: Access 16-bit array element (halfword)
    # ldrh.w r1, [r4, r0, lsl #1]
    index_shifted_half = ShiftedGeneralPurposeRegister(r0, 'LSL', 1)
    inst3 = LDRH_W(r1, [r4, index_shifted_half])
    print(f"3. {str(inst3):40s} # Load halfword, index * 2")
    
    # Example 4: Access byte array (just register offset)
    # ldrb.w r2, [r6, #0]
    inst4 = LDRB_W(r2, [r6])
    print(f"4. {str(inst4):40s} # Load byte, no offset")
    
    # Example 5: Using LSR (Logical Shift Right)
    # Useful for division by powers of 2
    # ldr.w r1, [r3, r2, lsr #2]
    index_shifted_lsr = ShiftedGeneralPurposeRegister(r2, 'LSR', 2)
    inst5 = LDR_W(r1, [r3, index_shifted_lsr])
    print(f"5. {str(inst5):40s} # LSR: index / 4")
    
    # Example 6: Using ASR (Arithmetic Shift Right)
    # Preserves sign bit during shift
    # ldr.w r0, [r4, r1, asr #3]
    index_shifted_asr = ShiftedGeneralPurposeRegister(r1, 'ASR', 3)
    inst6 = LDR_W(r0, [r4, index_shifted_asr])
    print(f"6. {str(inst6):40s} # ASR: signed index / 8")
    
    # Example 7: Using ROR (Rotate Right)
    # ldr.w r2, [r5, r3, ror #4]
    index_shifted_ror = ShiftedGeneralPurposeRegister(r3, 'ROR', 4)
    inst7 = LDR_W(r2, [r5, index_shifted_ror])
    print(f"7. {str(inst7):40s} # ROR: rotate index")


def example_array_traversal():
    """
    More realistic example: Traversing a 32-bit integer array.
    
    Equivalent C code:
        void process_array(int32_t* array, size_t length) {
            for (size_t i = 0; i < length; i++) {
                int32_t value = array[i];  // Uses ldr.w with shifted offset
                // process value...
            }
        }
    """
    print("\nExample 2: Array Traversal Pattern")
    print("=" * 60)
    print("# Assume: r0 = array base, r1 = index, r2 = value")
    
    # Create shifted index for 32-bit (4-byte) elements
    # This multiplies the index by 4 (left shift by 2)
    index_times_4 = ShiftedGeneralPurposeRegister(r1, 'LSL', 2)
    
    # Load: value = array[index]
    # Generates: ldr.w r2, [r0, r1, lsl #2]
    inst1 = LDR_W(r2, [r0, index_times_4])
    print(f"   {str(inst1):40s} # value = array[index]")
    
    # Process the value (example: store it back)
    # Generates: str.w r2, [r0, r1, lsl #2]
    inst2 = STR_W(r2, [r0, index_times_4])
    print(f"   {str(inst2):40s} # array[index] = value")


def example_different_element_sizes():
    """
    Show how to access arrays with different element sizes.
    """
    print("\nExample 3: Different Element Sizes")
    print("=" * 60)
    
    # 8-byte elements (double word) - use LSL #3
    index_shift_8 = ShiftedGeneralPurposeRegister(r1, 'LSL', 3)
    inst1 = LDR_W(r2, [r0, index_shift_8])
    print(f"   {str(inst1):40s} # 8-byte elements (LSL #3)")
    
    # 4-byte elements (word) - use LSL #2
    index_shift_4 = ShiftedGeneralPurposeRegister(r1, 'LSL', 2)
    inst2 = LDR_W(r2, [r0, index_shift_4])
    print(f"   {str(inst2):40s} # 4-byte elements (LSL #2)")
    
    # 2-byte elements (halfword) - use LSL #1
    index_shift_2 = ShiftedGeneralPurposeRegister(r1, 'LSL', 1)
    inst3 = LDRH_W(r2, [r0, index_shift_2])
    print(f"   {str(inst3):40s} # 2-byte elements (LSL #1)")
    
    # 1-byte elements (byte) - with immediate offset
    inst4 = LDRB_W(r2, [r0, 0])
    print(f"   {str(inst4):40s} # 1-byte elements (imm offset)")


def print_shift_constraints():
    """
    Print the constraints for different shift types.
    """
    print("\nShift Type Constraints:")
    print("=" * 60)
    print("LSL (Logical Shift Left):      1 to 31")
    print("LSR (Logical Shift Right):     1 to 32")
    print("ASR (Arithmetic Shift Right):  1 to 32")
    print("ROR (Rotate Right):            1 to 31")
    print("RRX (Rotate Right Extended):   No shift value (implicit 1)")
    print("=" * 60)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ARM Assembly with Shifted Register Offsets")
    print("=" * 60)
    
    # Generate examples
    example_shifted_load_store()
    example_array_traversal()
    example_different_element_sizes()
    
    # Print constraints
    print_shift_constraints()
    
    print("\n✓ All instructions generated successfully!")
    print("\nKey Point: Use ShiftedGeneralPurposeRegister to create")
    print("shifted register offsets for LDR_W and STR_W instructions.")
    print("\nUsage:")
    print("  from nervapy.arm.registers import ShiftedGeneralPurposeRegister")
    print("  shifted_reg = ShiftedGeneralPurposeRegister(r5, 'LSL', 2)")
    print("  LDR_W(r2, [r6, shifted_reg])  # Generates: ldr.w r2, [r6, r5, lsl #2]")
