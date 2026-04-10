"""
Test that dead output registers are properly allocated.

This tests the fix for a bug where registers that were written but never read
(dead code outputs) were not tracked for allocation, causing a RuntimeError.
"""

import unittest

from nervapy import *
from nervapy.arm import *
from nervapy.arm.abi import arm_gnueabihf


class TestDeadRegisterAllocation(unittest.TestCase):
    """Test that dead output registers are properly allocated."""
    
    def test_dead_output_register(self):
        """Test that a register written but never read is still allocated."""
        source_arg = Argument(ptr(uint32_t), name='source')
        
        with Function('test_dead', (source_arg,), abi=arm_gnueabihf) as f:
            src = LOAD.ARGUMENTS()[0]
            r = GeneralPurposeRegister()
            # r is written by LDR but never used - this is dead code
            # but should still allocate successfully
            LDR(r, [src])
            RETURN()
        
        # Should generate assembly without errors
        assembly = f.assembly
        self.assertIsNotNone(assembly)
        self.assertIn('LDR', assembly)
    
    def test_multiple_dead_outputs(self):
        """Test multiple dead output registers."""
        src_arg = Argument(ptr(uint32_t), name='src')
        
        with Function('test_multi_dead', (src_arg,), abi=arm_gnueabihf) as f:
            src = LOAD.ARGUMENTS()[0]
            r1 = GeneralPurposeRegister()
            r2 = GeneralPurposeRegister()
            r3 = GeneralPurposeRegister()
            
            # All three are dead outputs
            LDR(r1, [src])
            LDR(r2, [src, 4])
            LDR(r3, [src, 8])
            RETURN()
        
        assembly = f.assembly
        self.assertIsNotNone(assembly)
        # Should have 3 LDR instructions
        self.assertEqual(assembly.count('LDR'), 3)
    
    def test_mixed_live_and_dead(self):
        """Test mix of live and dead registers."""
        src_arg = Argument(ptr(uint32_t), name='src')
        dst_arg = Argument(ptr(uint32_t), name='dst')
        
        with Function('test_mixed', (src_arg, dst_arg), abi=arm_gnueabihf) as f:
            src, dst = LOAD.ARGUMENTS()
            live = GeneralPurposeRegister()
            dead = GeneralPurposeRegister()
            
            LDR(live, [src])    # live is used below
            LDR(dead, [src, 4]) # dead is never used
            STR(live, [dst])    # uses live
            RETURN()
        
        assembly = f.assembly
        self.assertIsNotNone(assembly)
        self.assertEqual(assembly.count('LDR'), 2)
        self.assertEqual(assembly.count('STR'), 1)


if __name__ == '__main__':
    unittest.main()
