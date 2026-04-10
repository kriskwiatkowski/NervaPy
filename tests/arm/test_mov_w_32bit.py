#!/usr/bin/env python3
"""
Test script demonstrating MOV.W with 32-bit modified immediates in NervaPy.

This shows that MOV.W #0x11111111 is valid in Thumb-2 because it uses
the "repeat byte pattern" encoding.
"""

import sys
sys.path.insert(0, '/home/kris/repos/NervaPy')

from nervapy.arm import *
from nervapy.arm.abi import arm_gnueabihf
from nervapy.arm.microarchitecture import Microarchitecture
from nervapy.arm.generic import MOVW, MOVT

print("=" * 70)
print("MOV.W with 32-bit Modified Immediates")
print("=" * 70)
print()

# Test 1: Using MOV_W (explicit .W suffix)
print("Test 1: Using MOV_W (explicit .W suffix)")
print("-" * 70)
f1 = Function("test_mov_w", (), abi=arm_gnueabihf, target=Microarchitecture.CortexM4)
with f1:
    MOV_W(r0, 0x11111111)  # Repeat 0x11
    MOV_W(r1, 0x22222222)  # Repeat 0x22
    MOV_W(r2, 0x33333333)  # Repeat 0x33
    MOV_W(r3, 0xFF00FF00)  # Alternating bytes
    BX(lr)

print(f1.assembly)
print()

# Test 2: Using regular MOV (assembler chooses encoding)
print("Test 2: Using MOV (assembler chooses encoding)")
print("-" * 70)
f2 = Function("test_mov", (), abi=arm_gnueabihf, target=Microarchitecture.CortexM4)
with f2:
    MOV(r0, 0x11111111)
    MOV(r1, 0x22222222)
    MOV(r2, 0xFF)  # Simple 8-bit value
    BX(lr)

print(f2.assembly)
print()

# Test 3: Demonstrating all pattern types
print("Test 3: Various modified immediate patterns")
print("-" * 70)
f3 = Function("test_patterns", (), abi=arm_gnueabihf, target=Microarchitecture.CortexM4)
with f3:
    MOV_W(r0, 0x000000AB)  # Pattern 0b00: 0x000000XY
    MOV_W(r1, 0x00CD00CD)  # Pattern 0b01: 0x00XY00XY
    MOV_W(r2, 0xEF00EF00)  # Pattern 0b10: 0xXY00XY00
    MOV_W(r3, 0x55555555)  # Pattern 0b11: 0xXYXYXYXY
    BX(lr)

print(f3.assembly)
print()

# Test 4: Compare with MOVW+MOVT for values that don't fit
print("Test 4: For values that don't fit modified immediate, use MOVW+MOVT")
print("-" * 70)
f4 = Function("test_movw_movt", (), abi=arm_gnueabihf, target=Microarchitecture.CortexM4)
with f4:
    # This value (0x12345678) does NOT fit modified immediate encoding
    MOVW(r0, 0x5678)  # Load lower 16 bits
    MOVT(r0, 0x1234)  # Load upper 16 bits
    BX(lr)

print(f4.assembly)
print()

print("=" * 70)
print("Summary:")
print("-" * 70)
print("✓ MOV_W() can load 32-bit values using modified immediate encoding")
print("✓ Works with repeating byte patterns like 0x11111111, 0x22222222")
print("✓ Also works with other patterns like 0xFF00FF00, 0x00AB00AB")
print("✓ For values that don't fit, use MOVW+MOVT or LDR with literal pool")
print("=" * 70)
