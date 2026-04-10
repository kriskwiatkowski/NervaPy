import unittest

from nervapy import *
from nervapy.arm import *
from nervapy.arm.abi import arm_gnueabihf
from nervapy.arm.formats import AssemblyFormat
from nervapy.arm.microarchitecture import Microarchitecture


class TestMultiplyInstructions(unittest.TestCase):
    """Test suite for ARM multiply instructions: MUL, MLA, UMAAL, UMAALGE, UMLAL, UMULL"""

    def test_mul_basic(self):
        """Test MUL - Basic 32-bit multiply instruction"""
        a_arg = Argument(uint32_t)
        b_arg = Argument(uint32_t)
        result_arg = Argument(ptr(uint32_t))
        
        with Function("test_mul", (a_arg, b_arg, result_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, result_ptr) = LOAD.ARGUMENTS()
            
            # MUL: r4 = a * b
            MUL(r4, a, b)
            STR(r4, [result_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("MUL", assembly)
        self.assertIn(".arch", assembly)

    def test_mla_multiply_accumulate(self):
        """Test MLA - Multiply-accumulate instruction"""
        a_arg = Argument(uint32_t)
        b_arg = Argument(uint32_t)
        c_arg = Argument(uint32_t)
        result_arg = Argument(ptr(uint32_t))
        
        with Function("test_mla", (a_arg, b_arg, c_arg, result_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, c, result_ptr) = LOAD.ARGUMENTS()
            
            # MLA: r4 = (a * b) + c
            MLA(r4, a, b, c)
            STR(r4, [result_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("MLA", assembly)

    def test_umull_unsigned_multiply_long(self):
        """Test UMULL - Unsigned multiply long (64-bit result)"""
        a_arg = Argument(uint32_t)
        b_arg = Argument(uint32_t)
        result_low_arg = Argument(ptr(uint32_t))
        result_high_arg = Argument(ptr(uint32_t))
        
        with Function("test_umull", (a_arg, b_arg, result_low_arg, result_high_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, result_low_ptr, result_high_ptr) = LOAD.ARGUMENTS()
            
            # UMULL: r5:r4 = a * b (unsigned, 64-bit result)
            UMULL(r4, r5, a, b)
            
            STR(r4, [result_low_ptr])
            STR(r5, [result_high_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("UMULL", assembly)
        # Verify both low and high registers
        self.assertIn("r4", assembly)
        self.assertIn("r5", assembly)

    def test_umlal_unsigned_multiply_accumulate_long(self):
        """Test UMLAL - Unsigned multiply-accumulate long"""
        a_arg = Argument(uint32_t)
        b_arg = Argument(uint32_t)
        acc_low_arg = Argument(uint32_t)
        acc_high_arg = Argument(uint32_t)
        result_low_arg = Argument(ptr(uint32_t))
        result_high_arg = Argument(ptr(uint32_t))
        
        with Function("test_umlal",
                     (a_arg, b_arg, acc_low_arg, acc_high_arg, result_low_arg, result_high_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, acc_low, acc_high, result_low_ptr, result_high_ptr) = LOAD.ARGUMENTS()
            
            # Initialize accumulators
            MOV(r4, acc_low)
            MOV(r5, acc_high)
            
            # UMLAL: r5:r4 += a * b (unsigned, 64-bit accumulate)
            UMLAL(r4, r5, a, b)
            
            STR(r4, [result_low_ptr])
            STR(r5, [result_high_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("UMLAL", assembly)

    def test_umaal_double_accumulate(self):
        """Test UMAAL - Unsigned multiply-accumulate-accumulate long"""
        a_arg = Argument(uint32_t)
        b_arg = Argument(uint32_t)
        acc1_arg = Argument(uint32_t)
        acc2_arg = Argument(uint32_t)
        result_low_arg = Argument(ptr(uint32_t))
        result_high_arg = Argument(ptr(uint32_t))
        
        with Function("test_umaal",
                     (a_arg, b_arg, acc1_arg, acc2_arg, result_low_arg, result_high_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, acc1, acc2, result_low_ptr, result_high_ptr) = LOAD.ARGUMENTS()
            
            # Initialize accumulators
            MOV(r4, acc1)
            MOV(r5, acc2)
            
            # UMAAL: r5:r4 = (a * b) + r4 + r5
            UMAAL(r4, r5, a, b)
            
            STR(r4, [result_low_ptr])
            STR(r5, [result_high_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("UMAAL", assembly)

    def test_umaalge_conditional(self):
        """Test UMAALGE - Conditional UMAAL (Greater or Equal)"""
        a_arg = Argument(uint32_t)
        b_arg = Argument(uint32_t)
        c_arg = Argument(uint32_t)
        acc1_arg = Argument(uint32_t)
        acc2_arg = Argument(uint32_t)
        result_low_arg = Argument(ptr(uint32_t))
        result_high_arg = Argument(ptr(uint32_t))
        
        with Function("test_umaalge",
                     (a_arg, b_arg, c_arg, acc1_arg, acc2_arg, result_low_arg, result_high_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, c, acc1, acc2, result_low_ptr, result_high_ptr) = LOAD.ARGUMENTS()
            
            # Initialize accumulators
            MOV(r4, acc1)
            MOV(r5, acc2)
            
            # Compare a with c to set condition flags
            CMP(a, c)
            
            # UMAALGE: if (a >= c) then r5:r4 = (a * b) + r4 + r5
            UMAALGE(r4, r5, a, b)
            
            STR(r4, [result_low_ptr])
            STR(r5, [result_high_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("UMAALGE", assembly)
        self.assertIn("CMP", assembly)

    def test_combined_multiply_operations(self):
        """Test combining multiple multiply instructions in one function"""
        a_arg = Argument(uint32_t)
        b_arg = Argument(uint32_t)
        c_arg = Argument(uint32_t)
        result_arg = Argument(ptr(uint32_t))
        
        with Function("test_combined",
                     (a_arg, b_arg, c_arg, result_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, c, result_ptr) = LOAD.ARGUMENTS()
            
            # Basic multiply
            MUL(r4, a, b)
            STR(r4, [result_ptr])
            
            # Multiply-accumulate
            MLA(r5, a, b, c)
            STR(r5, [result_ptr, 4])
            
            # Long multiply
            UMULL(r6, r7, a, b)
            STR(r6, [result_ptr, 8])
            STR(r7, [result_ptr, 12])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("MUL", assembly)
        self.assertIn("MLA", assembly)
        self.assertIn("UMULL", assembly)

    def test_mul_with_cortex_m4(self):
        """Test MUL instruction on Cortex-M4 (ARMv7-M)"""
        a_arg = Argument(uint32_t)
        b_arg = Argument(uint32_t)
        result_arg = Argument(ptr(uint32_t))
        
        with Function("test_mul_m4", (a_arg, b_arg, result_arg),
                     target=Microarchitecture.CortexM4,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, result_ptr) = LOAD.ARGUMENTS()
            
            MUL(r4, a, b)
            STR(r4, [result_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("MUL", assembly)
        self.assertIn(".arch armv7-m", assembly)

    def test_long_multiply_chain(self):
        """Test chaining UMULL and UMLAL for multi-precision arithmetic"""
        a_arg = Argument(uint32_t)
        b_arg = Argument(uint32_t)
        c_arg = Argument(uint32_t)
        d_arg = Argument(uint32_t)
        result_low_arg = Argument(ptr(uint32_t))
        result_high_arg = Argument(ptr(uint32_t))
        
        with Function("test_multiply_chain",
                     (a_arg, b_arg, c_arg, d_arg, result_low_arg, result_high_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, c, d, result_low_ptr, result_high_ptr) = LOAD.ARGUMENTS()
            
            # Compute (a*b) + (c*d) using UMULL and UMLAL
            # First: r5:r4 = a * b
            UMULL(r4, r5, a, b)
            
            # Then: r5:r4 += c * d
            UMLAL(r4, r5, c, d)
            
            STR(r4, [result_low_ptr])
            STR(r5, [result_high_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("UMULL", assembly)
        self.assertIn("UMLAL", assembly)


class TestMultiplyInstructionsARMCC(unittest.TestCase):
    """Test multiply instructions with ARMCC assembly format"""

    def test_mul_armcc_format(self):
        """Test MUL instruction with ARMCC format"""
        a_arg = Argument(uint32_t)
        b_arg = Argument(uint32_t)
        result_arg = Argument(ptr(uint32_t))
        
        with Function("test_mul_armcc", (a_arg, b_arg, result_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.ARMCC,
                     report_generation=False) as function:
            (a, b, result_ptr) = LOAD.ARGUMENTS()
            
            MUL(r4, a, b)
            STR(r4, [result_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("MUL", assembly)
        self.assertIn("AREA", assembly)
        self.assertIn("PROC", assembly)

    def test_umull_armcc_format(self):
        """Test UMULL instruction with ARMCC format"""
        a_arg = Argument(uint32_t)
        b_arg = Argument(uint32_t)
        result_low_arg = Argument(ptr(uint32_t))
        result_high_arg = Argument(ptr(uint32_t))
        
        with Function("test_umull_armcc", (a_arg, b_arg, result_low_arg, result_high_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.ARMCC,
                     report_generation=False) as function:
            (a, b, result_low_ptr, result_high_ptr) = LOAD.ARGUMENTS()
            
            UMULL(r4, r5, a, b)
            
            STR(r4, [result_low_ptr])
            STR(r5, [result_high_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("UMULL", assembly)
        self.assertIn("ENDP", assembly)


class TestSignedMultiplyInstructions(unittest.TestCase):
    """Test suite for signed multiply instructions: SMULL, SMLAL"""

    def test_smull_signed_multiply_long(self):
        """Test SMULL - Signed multiply long (64-bit result)"""
        a_arg = Argument(int32_t)
        b_arg = Argument(int32_t)
        result_low_arg = Argument(ptr(uint32_t))
        result_high_arg = Argument(ptr(uint32_t))
        
        with Function("test_smull", (a_arg, b_arg, result_low_arg, result_high_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, result_low_ptr, result_high_ptr) = LOAD.ARGUMENTS()
            
            # SMULL: r5:r4 = a * b (signed, 64-bit result)
            SMULL(r4, r5, a, b)
            
            STR(r4, [result_low_ptr])
            STR(r5, [result_high_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("SMULL", assembly)

    def test_smlal_signed_multiply_accumulate_long(self):
        """Test SMLAL - Signed multiply-accumulate long"""
        a_arg = Argument(int32_t)
        b_arg = Argument(int32_t)
        acc_low_arg = Argument(uint32_t)
        acc_high_arg = Argument(uint32_t)
        result_low_arg = Argument(ptr(uint32_t))
        result_high_arg = Argument(ptr(uint32_t))
        
        with Function("test_smlal",
                     (a_arg, b_arg, acc_low_arg, acc_high_arg, result_low_arg, result_high_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, acc_low, acc_high, result_low_ptr, result_high_ptr) = LOAD.ARGUMENTS()
            
            # Initialize accumulators
            MOV(r4, acc_low)
            MOV(r5, acc_high)
            
            # SMLAL: r5:r4 += a * b (signed, 64-bit accumulate)
            SMLAL(r4, r5, a, b)
            
            STR(r4, [result_low_ptr])
            STR(r5, [result_high_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("SMLAL", assembly)


class TestDSPMultiplyInstructions(unittest.TestCase):
    """Test suite for DSP multiply instructions"""

    def test_mls_multiply_subtract(self):
        """Test MLS - Multiply and subtract"""
        a_arg = Argument(uint32_t)
        b_arg = Argument(uint32_t)
        c_arg = Argument(uint32_t)
        result_arg = Argument(ptr(uint32_t))
        
        with Function("test_mls", (a_arg, b_arg, c_arg, result_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, c, result_ptr) = LOAD.ARGUMENTS()
            
            # MLS: r4 = c - (a * b)
            MLS(r4, a, b, c)
            STR(r4, [result_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("MLS", assembly)

    def test_smultbeq_conditional(self):
        """Test SMULTBEQ - Conditional signed multiply top-bottom"""
        a_arg = Argument(uint32_t)
        b_arg = Argument(uint32_t)
        c_arg = Argument(uint32_t)
        result_arg = Argument(ptr(uint32_t))
        
        with Function("test_smultbeq", (a_arg, b_arg, c_arg, result_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, c, result_ptr) = LOAD.ARGUMENTS()
            
            # Set condition with CMP
            CMP(a, c)
            
            # SMULTBEQ: if EQ, r4 = a[31:16] * b[15:0]
            SMULTBEQ(r4, a, b)
            STR(r4, [result_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("SMULTBEQ", assembly)
        self.assertIn("CMP", assembly)

    def test_smlabbne_conditional(self):
        """Test SMLABBNE - Conditional signed multiply-accumulate bottom-bottom"""
        a_arg = Argument(uint32_t)
        b_arg = Argument(uint32_t)
        c_arg = Argument(uint32_t)
        d_arg = Argument(uint32_t)
        result_arg = Argument(ptr(uint32_t))
        
        with Function("test_smlabbne", (a_arg, b_arg, c_arg, d_arg, result_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, c, d, result_ptr) = LOAD.ARGUMENTS()
            
            # Set condition
            CMP(a, d)
            
            # SMLABBNE: if NE, r4 = (a[15:0] * b[15:0]) + c
            SMLABBNE(r4, a, b, c)
            STR(r4, [result_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("SMLABBNE", assembly)

    def test_smlabt(self):
        """Test SMLABT - Signed multiply-accumulate bottom-top"""
        a_arg = Argument(uint32_t)
        b_arg = Argument(uint32_t)
        c_arg = Argument(uint32_t)
        result_arg = Argument(ptr(uint32_t))
        
        with Function("test_smlabt", (a_arg, b_arg, c_arg, result_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, c, result_ptr) = LOAD.ARGUMENTS()
            
            # SMLABT: r4 = (a[15:0] * b[31:16]) + c
            SMLABT(r4, a, b, c)
            STR(r4, [result_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("SMLABT", assembly)

    def test_smlawb(self):
        """Test SMLAWB - Signed multiply-accumulate word bottom"""
        a_arg = Argument(int32_t)
        b_arg = Argument(int32_t)
        c_arg = Argument(int32_t)
        result_arg = Argument(ptr(uint32_t))
        
        with Function("test_smlawb", (a_arg, b_arg, c_arg, result_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, c, result_ptr) = LOAD.ARGUMENTS()
            
            # SMLAWB: r4 = ((a * b[15:0]) >> 16) + c
            SMLAWB(r4, a, b, c)
            STR(r4, [result_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("SMLAWB", assembly)

    def test_smlawt(self):
        """Test SMLAWT - Signed multiply-accumulate word top"""
        a_arg = Argument(int32_t)
        b_arg = Argument(int32_t)
        c_arg = Argument(int32_t)
        result_arg = Argument(ptr(uint32_t))
        
        with Function("test_smlawt", (a_arg, b_arg, c_arg, result_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, c, result_ptr) = LOAD.ARGUMENTS()
            
            # SMLAWT: r4 = ((a * b[31:16]) >> 16) + c
            SMLAWT(r4, a, b, c)
            STR(r4, [result_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("SMLAWT", assembly)

    def test_smulwb(self):
        """Test SMULWB - Signed multiply word bottom"""
        a_arg = Argument(int32_t)
        b_arg = Argument(int32_t)
        result_arg = Argument(ptr(uint32_t))
        
        with Function("test_smulwb", (a_arg, b_arg, result_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, result_ptr) = LOAD.ARGUMENTS()
            
            # SMULWB: r4 = (a * b[15:0]) >> 16
            SMULWB(r4, a, b)
            STR(r4, [result_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("SMULWB", assembly)

    def test_smulwt(self):
        """Test SMULWT - Signed multiply word top"""
        a_arg = Argument(int32_t)
        b_arg = Argument(int32_t)
        result_arg = Argument(ptr(uint32_t))
        
        with Function("test_smulwt", (a_arg, b_arg, result_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, result_ptr) = LOAD.ARGUMENTS()
            
            # SMULWT: r4 = (a * b[31:16]) >> 16
            SMULWT(r4, a, b)
            STR(r4, [result_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("SMULWT", assembly)


class TestMSWMultiplyInstructions(unittest.TestCase):
    """Test suite for Most Significant Word multiply instructions"""

    def test_smmul(self):
        """Test SMMUL - Signed most significant word multiply"""
        a_arg = Argument(int32_t)
        b_arg = Argument(int32_t)
        result_arg = Argument(ptr(uint32_t))
        
        with Function("test_smmul", (a_arg, b_arg, result_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, result_ptr) = LOAD.ARGUMENTS()
            
            # SMMUL: r4 = (a * b)[63:32]
            SMMUL(r4, a, b)
            STR(r4, [result_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("SMMUL", assembly)

    def test_smmla(self):
        """Test SMMLA - Signed MSW multiply-accumulate"""
        a_arg = Argument(int32_t)
        b_arg = Argument(int32_t)
        c_arg = Argument(int32_t)
        result_arg = Argument(ptr(uint32_t))
        
        with Function("test_smmla", (a_arg, b_arg, c_arg, result_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, c, result_ptr) = LOAD.ARGUMENTS()
            
            # SMMLA: r4 = ((a * b)[63:32]) + c
            SMMLA(r4, a, b, c)
            STR(r4, [result_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("SMMLA", assembly)

    def test_smmls(self):
        """Test SMMLS - Signed MSW multiply-subtract"""
        a_arg = Argument(int32_t)
        b_arg = Argument(int32_t)
        c_arg = Argument(int32_t)
        result_arg = Argument(ptr(uint32_t))
        
        with Function("test_smmls", (a_arg, b_arg, c_arg, result_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, c, result_ptr) = LOAD.ARGUMENTS()
            
            # SMMLS: r4 = c - ((a * b)[63:32])
            SMMLS(r4, a, b, c)
            STR(r4, [result_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("SMMLS", assembly)


class TestSIMDMultiplyInstructions(unittest.TestCase):
    """Test suite for SIMD dual multiply instructions"""

    def test_smlad(self):
        """Test SMLAD - Signed dual multiply-add"""
        a_arg = Argument(uint32_t)
        b_arg = Argument(uint32_t)
        c_arg = Argument(uint32_t)
        result_arg = Argument(ptr(uint32_t))
        
        with Function("test_smlad", (a_arg, b_arg, c_arg, result_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, c, result_ptr) = LOAD.ARGUMENTS()
            
            # SMLAD: r4 = (a[15:0]*b[15:0]) + (a[31:16]*b[31:16]) + c
            SMLAD(r4, a, b, c)
            STR(r4, [result_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("SMLAD", assembly)

    def test_smlsd(self):
        """Test SMLSD - Signed dual multiply-subtract"""
        a_arg = Argument(uint32_t)
        b_arg = Argument(uint32_t)
        c_arg = Argument(uint32_t)
        result_arg = Argument(ptr(uint32_t))
        
        with Function("test_smlsd", (a_arg, b_arg, c_arg, result_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, c, result_ptr) = LOAD.ARGUMENTS()
            
            # SMLSD: r4 = (a[15:0]*b[15:0]) - (a[31:16]*b[31:16]) + c
            SMLSD(r4, a, b, c)
            STR(r4, [result_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("SMLSD", assembly)

    def test_smlald(self):
        """Test SMLALD - Signed dual multiply-add long"""
        a_arg = Argument(uint32_t)
        b_arg = Argument(uint32_t)
        acc_low_arg = Argument(uint32_t)
        acc_high_arg = Argument(uint32_t)
        result_low_arg = Argument(ptr(uint32_t))
        result_high_arg = Argument(ptr(uint32_t))
        
        with Function("test_smlald",
                     (a_arg, b_arg, acc_low_arg, acc_high_arg, result_low_arg, result_high_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, acc_low, acc_high, result_low_ptr, result_high_ptr) = LOAD.ARGUMENTS()
            
            MOV(r4, acc_low)
            MOV(r5, acc_high)
            
            # SMLALD: r5:r4 += (a[15:0]*b[15:0]) + (a[31:16]*b[31:16])
            SMLALD(r4, r5, a, b)
            
            STR(r4, [result_low_ptr])
            STR(r5, [result_high_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("SMLALD", assembly)

    def test_smlsld(self):
        """Test SMLSLD - Signed dual multiply-subtract long"""
        a_arg = Argument(uint32_t)
        b_arg = Argument(uint32_t)
        acc_low_arg = Argument(uint32_t)
        acc_high_arg = Argument(uint32_t)
        result_low_arg = Argument(ptr(uint32_t))
        result_high_arg = Argument(ptr(uint32_t))
        
        with Function("test_smlsld",
                     (a_arg, b_arg, acc_low_arg, acc_high_arg, result_low_arg, result_high_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, acc_low, acc_high, result_low_ptr, result_high_ptr) = LOAD.ARGUMENTS()
            
            MOV(r4, acc_low)
            MOV(r5, acc_high)
            
            # SMLSLD: r5:r4 += (a[15:0]*b[15:0]) - (a[31:16]*b[31:16])
            SMLSLD(r4, r5, a, b)
            
            STR(r4, [result_low_ptr])
            STR(r5, [result_high_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("SMLSLD", assembly)


class TestSMLALVariants(unittest.TestCase):
    """Test suite for SMLAL halfword variants"""

    def test_smlalbb(self):
        """Test SMLALBB - Signed multiply-accumulate long bottom-bottom"""
        a_arg = Argument(int32_t)
        b_arg = Argument(int32_t)
        acc_low_arg = Argument(uint32_t)
        acc_high_arg = Argument(uint32_t)
        result_low_arg = Argument(ptr(uint32_t))
        result_high_arg = Argument(ptr(uint32_t))
        
        with Function("test_smlalbb",
                     (a_arg, b_arg, acc_low_arg, acc_high_arg, result_low_arg, result_high_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, acc_low, acc_high, result_low_ptr, result_high_ptr) = LOAD.ARGUMENTS()
            
            MOV(r4, acc_low)
            MOV(r5, acc_high)
            
            # SMLALBB: r5:r4 += a[15:0] * b[15:0]
            SMLALBB(r4, r5, a, b)
            
            STR(r4, [result_low_ptr])
            STR(r5, [result_high_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("SMLALBB", assembly)

    def test_smlalbt(self):
        """Test SMLALBT - Signed multiply-accumulate long bottom-top"""
        a_arg = Argument(int32_t)
        b_arg = Argument(int32_t)
        acc_low_arg = Argument(uint32_t)
        acc_high_arg = Argument(uint32_t)
        result_low_arg = Argument(ptr(uint32_t))
        result_high_arg = Argument(ptr(uint32_t))
        
        with Function("test_smlalbt",
                     (a_arg, b_arg, acc_low_arg, acc_high_arg, result_low_arg, result_high_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, acc_low, acc_high, result_low_ptr, result_high_ptr) = LOAD.ARGUMENTS()
            
            MOV(r4, acc_low)
            MOV(r5, acc_high)
            
            # SMLALBT: r5:r4 += a[15:0] * b[31:16]
            SMLALBT(r4, r5, a, b)
            
            STR(r4, [result_low_ptr])
            STR(r5, [result_high_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("SMLALBT", assembly)

    def test_smlaltb(self):
        """Test SMLALTB - Signed multiply-accumulate long top-bottom"""
        a_arg = Argument(int32_t)
        b_arg = Argument(int32_t)
        acc_low_arg = Argument(uint32_t)
        acc_high_arg = Argument(uint32_t)
        result_low_arg = Argument(ptr(uint32_t))
        result_high_arg = Argument(ptr(uint32_t))
        
        with Function("test_smlaltb",
                     (a_arg, b_arg, acc_low_arg, acc_high_arg, result_low_arg, result_high_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, acc_low, acc_high, result_low_ptr, result_high_ptr) = LOAD.ARGUMENTS()
            
            MOV(r4, acc_low)
            MOV(r5, acc_high)
            
            # SMLALTB: r5:r4 += a[31:16] * b[15:0]
            SMLALTB(r4, r5, a, b)
            
            STR(r4, [result_low_ptr])
            STR(r5, [result_high_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("SMLALTB", assembly)

    def test_smlaltt(self):
        """Test SMLALTT - Signed multiply-accumulate long top-top"""
        a_arg = Argument(int32_t)
        b_arg = Argument(int32_t)
        acc_low_arg = Argument(uint32_t)
        acc_high_arg = Argument(uint32_t)
        result_low_arg = Argument(ptr(uint32_t))
        result_high_arg = Argument(ptr(uint32_t))
        
        with Function("test_smlaltt",
                     (a_arg, b_arg, acc_low_arg, acc_high_arg, result_low_arg, result_high_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, acc_low, acc_high, result_low_ptr, result_high_ptr) = LOAD.ARGUMENTS()
            
            MOV(r4, acc_low)
            MOV(r5, acc_high)
            
            # SMLALTT: r5:r4 += a[31:16] * b[31:16]
            SMLALTT(r4, r5, a, b)
            
            STR(r4, [result_low_ptr])
            STR(r5, [result_high_ptr])
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("SMLALTT", assembly)


class TestWMMXMultiplyInstructions(unittest.TestCase):
    """Test suite for Wireless MMX multiply instructions"""

    def test_mia(self):
        """Test MIA - Multiply with internal accumulate"""
        a_arg = Argument(uint32_t)
        b_arg = Argument(uint32_t)
        result_arg = Argument(ptr(uint32_t))
        
        with Function("test_mia", (a_arg, b_arg, result_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, result_ptr) = LOAD.ARGUMENTS()
            
            # MIA: wcgr0 += a * b
            MIA("wcgr0", a, b)
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("MIA", assembly)

    def test_miaph(self):
        """Test MIAPH - MIA packed halfwords"""
        a_arg = Argument(uint32_t)
        b_arg = Argument(uint32_t)
        result_arg = Argument(ptr(uint32_t))
        
        with Function("test_miaph", (a_arg, b_arg, result_arg),
                     target=Microarchitecture.ARM11,
                     abi=arm_gnueabihf,
                     assembly_format=AssemblyFormat.GAS,
                     report_generation=False) as function:
            (a, b, result_ptr) = LOAD.ARGUMENTS()
            
            # MIAPH: wcgr0 += (a[15:0]*b[15:0]) + (a[31:16]*b[31:16])
            MIAPH("wcgr0", a, b)
            
            RETURN()
        
        assembly = function.assembly
        self.assertIn("MIAPH", assembly)


if __name__ == '__main__':
    unittest.main()
