#!/usr/bin/env python3
"""Test barrel shifter with AND instruction"""

import unittest
from nervapy import *
from nervapy.arm import *
from nervapy.arm.abi import arm_gnueabihf
from nervapy.arm.formats import AssemblyFormat


class TestBarrelShifter(unittest.TestCase):
    """Test barrel shifter functionality with ARM instructions"""

    def test_and_with_shifted_source(self):
        """Test AND with one operand shifted (destination is also source)"""
        with Function("test_and_shifted", (), 
                      abi=arm_gnueabihf,
                      assembly_format=AssemblyFormat.GAS,
                      report_generation=False) as func:
            
            tr2 = GeneralPurposeRegister()
            tm = GeneralPurposeRegister()
            
            # tr2 = tr2 & (tm << 1)
            AND(tr2, tm.LSL(1))
            
            RETURN()
        
        assembly = func.assembly
        self.assertIn("AND", assembly)
        self.assertIn("LSL", assembly)

    def test_and_with_explicit_destination_and_shifted(self):
        """Test AND with two register operands and one shifted"""
        with Function("test_and_explicit", (), 
                      abi=arm_gnueabihf,
                      assembly_format=AssemblyFormat.GAS,
                      report_generation=False) as func:
            
            tr2 = GeneralPurposeRegister()
            tm = GeneralPurposeRegister()
            
            # tr2 = tr2 & (tm << 1)
            AND(tr2, tr2, tm.LSL(1))
            
            RETURN()
        
        assembly = func.assembly
        self.assertIn("AND", assembly)
        self.assertIn("LSL", assembly)

    def test_and_with_shifted_destination_raises_error(self):
        """Test that shifting destination register raises an error"""
        with self.assertRaises(ValueError):
            with Function("test_shifted_dest", (), 
                          abi=arm_gnueabihf,
                          assembly_format=AssemblyFormat.GAS,
                          report_generation=False) as func:
                
                tr2 = GeneralPurposeRegister()
                tm = GeneralPurposeRegister()
                
                # This should fail: can't shift destination
                AND(tr2.LSL(1), tm)
                
                RETURN()

    def test_and_with_both_operands_shifted_raises_error(self):
        """Test that shifting both operands raises an error"""
        with self.assertRaises(ValueError):
            with Function("test_both_shifted", (), 
                          abi=arm_gnueabihf,
                          assembly_format=AssemblyFormat.GAS,
                          report_generation=False) as func:
                
                tr2 = GeneralPurposeRegister()
                tm = GeneralPurposeRegister()
                
                # This should fail: can't shift multiple source operands in ARM
                AND(tr2, tr2.LSL(1), tm.LSL(1))
                
                RETURN()

    def test_and_then_shift_separate_instructions(self):
        """Test combining AND and LSL as separate instructions"""
        with Function("test_and_then_shift", (), 
                      abi=arm_gnueabihf,
                      assembly_format=AssemblyFormat.GAS,
                      report_generation=False) as func:
            
            tr2 = GeneralPurposeRegister()
            tm = GeneralPurposeRegister()
            
            # Two separate instructions: (tr2 & tm) << 1
            AND(tr2, tr2, tm)    # tr2 = tr2 & tm
            LSL(tr2, tr2, 1)     # tr2 = tr2 << 1
            
            RETURN()
        
        assembly = func.assembly
        self.assertIn("AND", assembly)
        self.assertIn("LSL", assembly)
        # Verify both instructions are present
        and_count = assembly.count("AND")
        lsl_count = assembly.count("LSL")
        self.assertGreaterEqual(and_count, 1)
        self.assertGreaterEqual(lsl_count, 1)

    def test_barrel_shifter_with_lsr(self):
        """Test barrel shifter with LSR (logical shift right)"""
        with Function("test_lsr", (), 
                      abi=arm_gnueabihf,
                      assembly_format=AssemblyFormat.GAS,
                      report_generation=False) as func:
            
            tr2 = GeneralPurposeRegister()
            tm = GeneralPurposeRegister()
            
            # tr2 = tr2 & (tm >> 2)
            AND(tr2, tm.LSR(2))
            
            RETURN()
        
        assembly = func.assembly
        self.assertIn("AND", assembly)
        self.assertIn("LSR", assembly)

    def test_barrel_shifter_with_asr(self):
        """Test barrel shifter with ASR (arithmetic shift right)"""
        with Function("test_asr", (), 
                      abi=arm_gnueabihf,
                      assembly_format=AssemblyFormat.GAS,
                      report_generation=False) as func:
            
            tr2 = GeneralPurposeRegister()
            tm = GeneralPurposeRegister()
            
            # tr2 = tr2 & (tm ASR 3)
            AND(tr2, tm.ASR(3))
            
            RETURN()
        
        assembly = func.assembly
        self.assertIn("AND", assembly)
        self.assertIn("ASR", assembly)

    def test_barrel_shifter_with_ror(self):
        """Test barrel shifter with ROR (rotate right)"""
        with Function("test_ror", (), 
                      abi=arm_gnueabihf,
                      assembly_format=AssemblyFormat.GAS,
                      report_generation=False) as func:
            
            tr2 = GeneralPurposeRegister()
            tm = GeneralPurposeRegister()
            
            # tr2 = tr2 & (tm ROR 4)
            AND(tr2, tm.ROR(4))
            
            RETURN()
        
        assembly = func.assembly
        self.assertIn("AND", assembly)
        self.assertIn("ROR", assembly)


if __name__ == '__main__':
    unittest.main()
