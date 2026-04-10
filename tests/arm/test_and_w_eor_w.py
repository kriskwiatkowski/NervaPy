#!/usr/bin/env python3
"""Test AND.W and EOR.W instructions with 32-bit modified immediates."""

import sys
sys.path.insert(0, '/home/kris/repos/NervaPy')

from nervapy.arm import *
from nervapy.arm.abi import arm_gnueabihf
from nervapy.arm.microarchitecture import Microarchitecture

print("=" * 70)
print("AND.W and EOR.W with 32-bit Modified Immediates")
print("=" * 70)
print()

# Test 1: AND.W with repeating byte patterns
print("Test 1: AND.W with repeating byte patterns")
print("-" * 70)
f1 = Function("test_and_w", (), abi=arm_gnueabihf, target=Microarchitecture.CortexM4)
with f1:
    AND_W(r0, r1, 0x11111111)  # Repeat 0x11
    AND_W(r2, r3, 0x22222222)  # Repeat 0x22
    AND_W(r4, 0xFFFFFFFF)      # Two-operand form
    AND_W(r5, r6, 0xABABABAB)  # Repeat 0xAB
    BX(lr)

print(f1.assembly)
print()

# Test 2: EOR.W with repeating byte patterns
print("Test 2: EOR.W with repeating byte patterns")
print("-" * 70)
f2 = Function("test_eor_w", (), abi=arm_gnueabihf, target=Microarchitecture.CortexM4)
with f2:
    EOR_W(r0, r1, 0x33333333)  # Repeat 0x33
    EOR_W(r2, r3, 0x44444444)  # Repeat 0x44
    EOR_W(r7, 0x12121212)      # Two-operand form
    EOR_W(r8, r9, 0xFEFEFEFE)  # Repeat 0xFE
    BX(lr)

print(f2.assembly)
print()

# Test 3: Mixed usage
print("Test 3: Mixed AND.W and EOR.W")
print("-" * 70)
f3 = Function("test_mixed", (), abi=arm_gnueabihf, target=Microarchitecture.CortexM4)
with f3:
    AND_W(r0, r1, 0x11111111)
    EOR_W(r2, r3, 0x22222222)
    AND_W(r4, 0x33333333)
    EOR_W(r5, 0x44444444)
    BX(lr)

print(f3.assembly)

print()
print("✓ All tests completed successfully!")

