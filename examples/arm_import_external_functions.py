#!/usr/bin/env python3
"""
Example: Using IMPORT for External Functions in ARMCC
======================================================

This example demonstrates how to declare external functions for ARMCC assembly
using the IMPORT directive.
"""

from nervapy.arm import (Function, IMPORT, BL, BX, MOV, CMP, BEQ,
                         r0, r1, r2, lr, Label)
from nervapy.arm.abi import arm_gnueabi
from nervapy.arm.formats import AssemblyFormat
from nervapy.arm.microarchitecture import Microarchitecture


def example_simple_external_call():
    """
    Example of calling an external function.
    """
    print("\n1. Simple External Function Call")
    print("=" * 70)
    
    with Function("my_function", (), None,
                  target=Microarchitecture.CortexM4,
                  abi=arm_gnueabi,
                  assembly_format=AssemblyFormat.ARMCC) as func:
        
        # Declare external function
        external_func = IMPORT.FUNCTION("printf")
        
        # Set up argument and call
        MOV(r0, 0x100)
        BL(external_func)
        
        # Return
        BX(lr)
    
    print("Generated ARMCC Assembly:")
    print("-" * 70)
    print(func.assembly)


def example_multiple_external_calls():
    """
    Example with multiple external functions.
    """
    print("\n2. Multiple External Function Calls")
    print("=" * 70)
    
    with Function("process_data", (), None,
                  target=Microarchitecture.CortexM4,
                  abi=arm_gnueabi,
                  assembly_format=AssemblyFormat.ARMCC) as func:
        
        # Declare external functions
        malloc_func = IMPORT.FUNCTION("malloc")
        memcpy_func = IMPORT.FUNCTION("memcpy")
        free_func = IMPORT.FUNCTION("free")
        
        # Call malloc
        MOV(r0, 256)
        BL(malloc_func)
        MOV(r1, r0)  # Save pointer
        
        # Call memcpy
        MOV(r0, r1)
        MOV(r1, r2)
        MOV(r2, 256)
        BL(memcpy_func)
        
        # Call free
        MOV(r0, r1)
        BL(free_func)
        
        # Return
        BX(lr)
    
    print("Generated ARMCC Assembly:")
    print("-" * 70)
    print(func.assembly)


def example_conditional_external_call():
    """
    Example with conditional external function call.
    """
    print("\n3. Conditional External Function Call")
    print("=" * 70)
    
    with Function("conditional_call", (), None,
                  target=Microarchitecture.CortexM4,
                  abi=arm_gnueabi,
                  assembly_format=AssemblyFormat.ARMCC) as func:
        
        # Declare external function
        error_handler = IMPORT.FUNCTION("handle_error")
        
        # Check condition
        CMP(r0, 0)
        skip_label = Label("skip_error")
        BEQ(skip_label)
        
        # Call error handler if r0 != 0
        BL(error_handler)
        
        # Skip label
        from nervapy.arm.pseudo import LABEL
        LABEL(skip_label)
        
        # Return
        BX(lr)
    
    print("Generated ARMCC Assembly:")
    print("-" * 70)
    print(func.assembly)


def example_comparison_gas_vs_armcc():
    """
    Compare GAS and ARMCC output for the same function.
    """
    print("\n4. Comparison: GAS vs ARMCC Format")
    print("=" * 70)
    
    # Generate with GAS format
    with Function("call_external", (), None,
                  target=Microarchitecture.CortexM4,
                  abi=arm_gnueabi,
                  assembly_format=AssemblyFormat.GAS) as func_gas:
        
        external_func = IMPORT.FUNCTION("external_function")
        MOV(r0, 42)
        BL(external_func)
        BX(lr)
    
    # Generate with ARMCC format
    with Function("call_external", (), None,
                  target=Microarchitecture.CortexM4,
                  abi=arm_gnueabi,
                  assembly_format=AssemblyFormat.ARMCC) as func_armcc:
        
        external_func = IMPORT.FUNCTION("external_function")
        MOV(r0, 42)
        BL(external_func)
        BX(lr)
    
    print("\nGAS Format:")
    print("-" * 70)
    print(func_gas.assembly)
    
    print("\nARMCC Format:")
    print("-" * 70)
    print(func_armcc.assembly)


def print_usage_summary():
    """
    Print usage summary.
    """
    print("\n" + "=" * 70)
    print("IMPORT Usage Summary")
    print("=" * 70)
    print("""
Basic Usage:
    from nervapy.arm import IMPORT, BL
    
    # Declare external function
    printf_func = IMPORT.FUNCTION("printf")
    
    # Call it
    BL(printf_func)

Key Points:
    • IMPORT.FUNCTION() declares an external function
    • For ARMCC, this generates an IMPORT directive
    • For GAS, no IMPORT directive is generated (not needed)
    • The function name is used directly (no 'L' prefix)
    • Multiple imports are automatically sorted and deduplicated
    • Works with both GAS and ARMCC assembly formats

ARMCC Output Format:
    AREA    ||.text||, CODE, READONLY
    IMPORT  external_function      ← Only in ARMCC format
    
    my_function    PROC
        EXPORT  my_function
        bl      external_function
        bx      lr
        ENDP
        END

GAS Output Format:
    .text
    .global my_function
    my_function:
        bl      external_function   ← No IMPORT needed
        bx      lr

Common External Functions:
    • printf, sprintf, snprintf  - Formatted output
    • malloc, free               - Memory allocation
    • memcpy, memset, memmove    - Memory operations
    • sin, cos, sqrt             - Math functions
    • Custom library functions
""")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("ARMCC External Function Import Examples")
    print("=" * 70)
    
    try:
        example_simple_external_call()
        example_multiple_external_calls()
        example_conditional_external_call()
        example_comparison_gas_vs_armcc()
        print_usage_summary()
        
        print("\n" + "=" * 70)
        print("✓ All examples completed successfully!")
        print("=" * 70)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
