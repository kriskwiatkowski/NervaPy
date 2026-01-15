#!/usr/bin/env python3
"""
Test ARMv7-M stack alignment validation for BL/BLX instructions.

According to ARM Architecture Reference Manual ARMv7-M and AAPCS:
- Stack must be 8-byte aligned at any public interface (function calls)
- This is enforced before BL and BLX instructions
- Only applies to ARMv7-M architecture (Cortex-M3, M4, M7)
"""

import unittest

from nervapy.arm import Function, BL, BLX, BX, PUSH, POP, SUB, ADD
from nervapy.arm.abi import arm_gnueabi
from nervapy.arm.formats import AssemblyFormat
from nervapy.arm.microarchitecture import Microarchitecture
from nervapy.arm.pseudo import IMPORT
from nervapy.arm.registers import r0, r1, r2, r3, r4, r5, r6, r7, sp, lr


class TestARMv7MStackAlignment(unittest.TestCase):
    """Test stack alignment validation for ARMv7-M architecture."""

    def test_misaligned_bl_detected(self):
        """Test that misaligned BL instruction is detected and raises error."""
        with self.assertRaises(ValueError) as cm:
            with Function("test_misaligned_bl", (), None,
                          target=Microarchitecture.CortexM4,
                          abi=arm_gnueabi,
                          assembly_format=AssemblyFormat.GAS,
                          report_generation=False) as func:
                external_func = IMPORT.FUNCTION("external_func")
                # Prologue adds PUSH {r3, r4} = 8 bytes
                # This adds 4 more bytes, making stack at +12 bytes (misaligned)
                PUSH((r4,))
                BL(external_func)
                POP((r4,))
                BX(lr)
        
        self.assertIn("Stack is not 8-byte aligned", str(cm.exception))
        self.assertIn("BL instruction", str(cm.exception))

    def test_aligned_bl_accepted(self):
        """Test that aligned BL instruction is accepted."""
        # This should not raise an exception
        with Function("test_aligned_bl", (), None,
                      target=Microarchitecture.CortexM4,
                      abi=arm_gnueabi,
                      assembly_format=AssemblyFormat.GAS,
                      report_generation=False) as func:
            external_func = IMPORT.FUNCTION("external_func")
            # Prologue adds PUSH {r3, r4} = 8 bytes
            # This adds 8 more bytes, keeping stack aligned at +16 bytes
            PUSH((r4, r5))
            BL(external_func)
            POP((r4, r5))
            BX(lr)
        
        # If we get here without exception, test passes
        self.assertIsNotNone(func.assembly)

    def test_misaligned_blx_detected(self):
        """Test that misaligned BLX instruction is detected and raises error."""
        with self.assertRaises(ValueError) as cm:
            with Function("test_misaligned_blx", (), None,
                          target=Microarchitecture.CortexM4,
                          abi=arm_gnueabi,
                          assembly_format=AssemblyFormat.GAS,
                          report_generation=False) as func:
                # Prologue adds PUSH {r3, r4} = 8 bytes
                # This adds 4 more bytes, making stack misaligned
                PUSH((r4,))
                BLX(r0)
                POP((r4,))
                BX(lr)
        
        self.assertIn("Stack is not 8-byte aligned", str(cm.exception))
        self.assertIn("BLX instruction", str(cm.exception))

    def test_aligned_blx_accepted(self):
        """Test that aligned BLX instruction is accepted."""
        with Function("test_aligned_blx", (), None,
                      target=Microarchitecture.CortexM4,
                      abi=arm_gnueabi,
                      assembly_format=AssemblyFormat.GAS,
                      report_generation=False) as func:
            PUSH((r4, r5))
            BLX(r0)
            POP((r4, r5))
            BX(lr)
        
        self.assertIsNotNone(func.assembly)

    def test_multiple_pushes_tracked(self):
        """Test that multiple PUSH/POP operations are tracked correctly."""
        with self.assertRaises(ValueError) as cm:
            with Function("test_multiple_pushes", (), None,
                          target=Microarchitecture.CortexM4,
                          abi=arm_gnueabi,
                          assembly_format=AssemblyFormat.GAS,
                          report_generation=False) as func:
                external_func = IMPORT.FUNCTION("external_func")
                # Prologue: +8 bytes (aligned)
                PUSH((r4, r5))  # +8 bytes = +16 total (aligned)
                PUSH((r6,))     # +4 bytes = +20 total (MISALIGNED)
                BL(external_func)
                POP((r6,))
                POP((r4, r5))
                BX(lr)
        
        self.assertIn("Stack is not 8-byte aligned", str(cm.exception))

    def test_push_pop_balance(self):
        """Test that PUSH/POP balance is tracked correctly."""
        with Function("test_push_pop_balance", (), None,
                      target=Microarchitecture.CortexM4,
                      abi=arm_gnueabi,
                      assembly_format=AssemblyFormat.GAS,
                      report_generation=False) as func:
            external_func = IMPORT.FUNCTION("external_func")
            # Prologue: +8 bytes (aligned)
            PUSH((r4, r5))  # +8 bytes = +16 (aligned)
            POP((r4, r5))   # -8 bytes = +8 (aligned)
            BL(external_func)
            BX(lr)
        
        self.assertIsNotNone(func.assembly)

    def test_cortex_m3_alignment(self):
        """Test alignment for Cortex-M3."""
        with self.assertRaises(ValueError):
            with Function("test_cortex_m3", (), None,
                          target=Microarchitecture.CortexM3,
                          abi=arm_gnueabi,
                          assembly_format=AssemblyFormat.GAS,
                          report_generation=False) as func:
                external_func = IMPORT.FUNCTION("external_func")
                PUSH((r4,))  # Misalign
                BL(external_func)
                POP((r4,))
                BX(lr)

    def test_cortex_m7_alignment(self):
        """Test alignment for Cortex-M7."""
        with self.assertRaises(ValueError):
            with Function("test_cortex_m7", (), None,
                          target=Microarchitecture.CortexM7,
                          abi=arm_gnueabi,
                          assembly_format=AssemblyFormat.GAS,
                          report_generation=False) as func:
                external_func = IMPORT.FUNCTION("external_func")
                PUSH((r4,))  # Misalign
                BL(external_func)
                POP((r4,))
                BX(lr)

    def test_non_armv7m_skipped(self):
        """Test that validation is skipped for non-ARMv7M architectures."""
        # Cortex-A8 is ARMv7-A, not ARMv7-M
        # Should not validate stack alignment
        with Function("test_cortex_a8", (), None,
                      target=Microarchitecture.CortexA8,
                      abi=arm_gnueabi,
                      assembly_format=AssemblyFormat.GAS,
                      report_generation=False) as func:
            external_func = IMPORT.FUNCTION("external_func")
            PUSH((r4,))  # Would be misaligned on ARMv7-M
            BL(external_func)
            POP((r4,))
            BX(lr)
        
        # Should complete without error
        self.assertIsNotNone(func.assembly)

    def test_validation_can_be_disabled(self):
        """Test that validation can be disabled with validate_stack_alignment=False."""
        # This should NOT raise an error even though stack is misaligned
        with Function("test_disabled_validation", (), None,
                      target=Microarchitecture.CortexM4,
                      abi=arm_gnueabi,
                      assembly_format=AssemblyFormat.GAS,
                      report_generation=False,
                      validate_stack_alignment=False) as func:
            external_func = IMPORT.FUNCTION("external_func")
            # Misalign stack
            PUSH((r4, r5))
            PUSH((r0,))  # Stack at +20 bytes (misaligned)
            BL(external_func)
            POP((r0,))
            POP((r4, r5))
            BX(lr)

        # Should complete without error
        self.assertIsNotNone(func.assembly)


if __name__ == '__main__':
    unittest.main()
