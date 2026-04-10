"""Test Cortex-M33 FPU directive generation"""

import unittest

from nervapy import *
from nervapy.arm import *
from nervapy.arm.abi import arm_gnueabihf
from nervapy.arm.formats import AssemblyFormat
from nervapy.arm.microarchitecture import Microarchitecture


class TestCortexM33FPU(unittest.TestCase):
    def test_cortex_m33_no_fpu_directive_without_fpu_usage(self):
        """Test that Cortex-M33 does NOT generate FPU directive when FPU is not used."""
        source_arg = Argument(ptr(const_uint32_t))
        destination_arg = Argument(ptr(uint32_t))

        with Function(
            "test_m33",
            (source_arg, destination_arg),
            target=Microarchitecture.CortexM33,
            abi=arm_gnueabihf,
            assembly_format=AssemblyFormat.GAS,
            report_generation=False,
        ) as test_func:
            (source, destination) = LOAD.ARGUMENTS()
            x = GeneralPurposeRegister()
            LDR(x, [source])
            STR(x, [destination])
            RETURN()

        assembly = test_func.assembly
        
        # Verify correct architecture
        self.assertIn(".arch armv8-m.main", assembly)
        
        # Should NOT have FPU directive when FPU is not used
        self.assertNotIn(".fpu", assembly)
        
        # Verify NEON is NOT present (Cortex-M33 doesn't support NEON)
        self.assertNotIn("neon", assembly.lower())

    def test_cortex_m33_integer_operations(self):
        """Test Cortex-M33 with integer-only operations."""
        source_arg = Argument(ptr(const_uint32_t))
        destination_arg = Argument(ptr(uint32_t))

        with Function(
            "test_m33_int",
            (source_arg, destination_arg),
            target=Microarchitecture.CortexM33,
            abi=arm_gnueabihf,
            assembly_format=AssemblyFormat.GAS,
            report_generation=False,
        ) as test_func:
            (source, destination) = LOAD.ARGUMENTS()
            x = GeneralPurposeRegister()
            LDR(x, [source])
            ADD(x, x, 1)
            STR(x, [destination])
            RETURN()

        assembly = test_func.assembly
        
        # Should have ARMv8-M architecture
        self.assertIn(".arch armv8-m.main", assembly)
        
        # Should NOT emit FPU directive for integer-only code
        self.assertNotIn(".fpu", assembly)
        
        # Must not have NEON
        self.assertNotIn("neon", assembly.lower())

    def test_cortex_a15_neon_unchanged(self):
        """Verify that Cortex-A15 (with NEON) still works correctly after M33 fix."""
        source_arg = Argument(ptr(const_uint32_t))
        destination_arg = Argument(ptr(uint32_t))

        with Function(
            "test_a15",
            (source_arg, destination_arg),
            target=Microarchitecture.CortexA15,
            abi=arm_gnueabihf,
            assembly_format=AssemblyFormat.GAS,
            report_generation=False,
        ) as test_func:
            (source, destination) = LOAD.ARGUMENTS()
            x = GeneralPurposeRegister()
            LDR(x, [source])
            STR(x, [destination])
            RETURN()

        assembly = test_func.assembly
        
        # Cortex-A15 should have NEON
        self.assertIn(".fpu neon-vfpv4", assembly)


if __name__ == "__main__":
    unittest.main()
