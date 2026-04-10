#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test PRESERVE8 directive for ARMCC assembly format.
"""

import sys
import os
# Ensure we're using the local development version
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))

from nervapy import *
from nervapy.arm import *
from nervapy.arm.abi import arm_gnueabihf
from nervapy.arm.formats import AssemblyFormat
from nervapy.arm.microarchitecture import Microarchitecture
import unittest


class TestPreserve8(unittest.TestCase):
    """Test PRESERVE8 directive for ARMCC assembly format."""
    
    def test_preserve8_disabled(self):
        """Test function without PRESERVE8 directive."""
        input_arg = Argument(ptr(const_uint32_t))
        output_arg = Argument(ptr(uint32_t))
        
        with Function("test_no_preserve8", (input_arg, output_arg),
                     target=Microarchitecture.CortexM3,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.ARMCC,
                     preserve8=False,
                     report_generation=False) as func:
            
            (input_ptr, output_ptr) = LOAD.ARGUMENTS()
            value = GeneralPurposeRegister()
            LDR(value, [input_ptr])
            STR(value, [output_ptr])
            RETURN()
        
        assembly = func.assembly
        # Verify PRESERVE8 is NOT in the assembly
        self.assertNotIn("PRESERVE8", assembly, "PRESERVE8 should not be present when preserve8=False")
    
    def test_preserve8_enabled(self):
        """Test function with PRESERVE8 directive."""
        input_arg = Argument(ptr(const_uint32_t))
        output_arg = Argument(ptr(uint32_t))
        
        with Function("test_with_preserve8", (input_arg, output_arg),
                     target=Microarchitecture.CortexM3,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.ARMCC,
                     preserve8=True,
                     report_generation=False) as func:
            
            (input_ptr, output_ptr) = LOAD.ARGUMENTS()
            value = GeneralPurposeRegister()
            LDR(value, [input_ptr])
            STR(value, [output_ptr])
            RETURN()
        
        assembly = func.assembly
        # Verify PRESERVE8 is in the assembly
        self.assertIn("PRESERVE8", assembly, "PRESERVE8 should be present when preserve8=True")
    
    def test_preserve8_gas_format(self):
        """Test that PRESERVE8 only applies to ARMCC format."""
        input_arg = Argument(ptr(const_uint32_t))
        output_arg = Argument(ptr(uint32_t))
        
        with Function("test_gas_preserve8", (input_arg, output_arg),
                     target=Microarchitecture.CortexM3,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     preserve8=True,
                     report_generation=False) as func:
            
            (input_ptr, output_ptr) = LOAD.ARGUMENTS()
            value = GeneralPurposeRegister()
            LDR(value, [input_ptr])
            STR(value, [output_ptr])
            RETURN()
        
        assembly = func.assembly
        # PRESERVE8 should not appear in GAS format
        self.assertNotIn("PRESERVE8", assembly, "PRESERVE8 should not be in GAS format")


if __name__ == "__main__":
    unittest.main()
