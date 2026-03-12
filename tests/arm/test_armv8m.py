import unittest

from nervapy import *
from nervapy.arm import *
from nervapy.arm.abi import arm_gnueabihf
from nervapy.arm.formats import AssemblyFormat
from nervapy.arm.microarchitecture import Microarchitecture


class TestARMv8MBase(unittest.TestCase):
    """Tests for ARMv8-M.base (Cortex-M23)."""

    def test_cortex_m23_gas_assembly(self):
        """Cortex-M23 emits armv8-m.base arch directive."""
        src_arg = Argument(ptr(const_uint32_t))
        dst_arg = Argument(ptr(uint32_t))
        len_arg = Argument(size_t)

        with Function("copy_words", (src_arg, dst_arg, len_arg),
                      target=Microarchitecture.CortexM23,
                      abi=arm_gnueabihf,
                      assembly_format=AssemblyFormat.GAS,
                      report_generation=False) as f:
            (src, dst, length) = LOAD.ARGUMENTS()

            with Loop() as loop:
                val = GeneralPurposeRegister()
                LDR(val, [src], 4)
                STR(val, [dst], 4)
                SUBS(length, 4)
                BNE(loop.begin)

            RETURN()

        assembly = f.assembly
        self.assertIn(".arch armv8-m.base", assembly)
        self.assertIn(".global copy_words", assembly)
        self.assertIn("copy_words:", assembly)

    def test_cortex_m23_armcc_assembly(self):
        """Cortex-M23 ARMCC assembly has standard PROC/ENDP structure."""
        src_arg = Argument(ptr(const_uint32_t))
        dst_arg = Argument(ptr(uint32_t))
        len_arg = Argument(size_t)

        with Function("copy_words_armcc", (src_arg, dst_arg, len_arg),
                      target=Microarchitecture.CortexM23,
                      abi=arm_gnueabihf,
                      assembly_format=AssemblyFormat.ARMCC,
                      report_generation=False) as f:
            (src, dst, length) = LOAD.ARGUMENTS()

            with Loop() as loop:
                val = GeneralPurposeRegister()
                LDR(val, [src], 4)
                STR(val, [dst], 4)
                SUBS(length, 4)
                BNE(loop.begin)

            RETURN()

        assembly = f.assembly
        self.assertIn("PROC", assembly)
        self.assertIn("ENDP", assembly)
        self.assertIn("EXPORT", assembly)


class TestARMv8MMain(unittest.TestCase):
    """Tests for ARMv8-M.main (Cortex-M33, Cortex-M35P)."""

    def test_cortex_m33_gas_assembly(self):
        """Cortex-M33 emits armv8-m.main arch directive."""
        src_arg = Argument(ptr(const_uint32_t))
        dst_arg = Argument(ptr(uint32_t))
        len_arg = Argument(size_t)

        with Function("add_one", (src_arg, dst_arg, len_arg),
                      target=Microarchitecture.CortexM33,
                      abi=arm_gnueabihf,
                      assembly_format=AssemblyFormat.GAS,
                      report_generation=False) as f:
            (src, dst, length) = LOAD.ARGUMENTS()

            with Loop() as loop:
                val = GeneralPurposeRegister()
                LDR(val, [src], 4)
                ADD(val, val, 1)
                STR(val, [dst], 4)
                SUBS(length, 4)
                BNE(loop.begin)

            RETURN()

        assembly = f.assembly
        self.assertIn(".arch armv8-m.main", assembly)
        self.assertIn(".global add_one", assembly)

    def test_cortex_m33_armcc_assembly(self):
        """Cortex-M33 ARMCC assembly has correct structure."""
        src_arg = Argument(ptr(const_uint32_t))
        dst_arg = Argument(ptr(uint32_t))
        len_arg = Argument(size_t)

        with Function("add_one_armcc", (src_arg, dst_arg, len_arg),
                      target=Microarchitecture.CortexM33,
                      abi=arm_gnueabihf,
                      assembly_format=AssemblyFormat.ARMCC,
                      report_generation=False) as f:
            (src, dst, length) = LOAD.ARGUMENTS()

            with Loop() as loop:
                val = GeneralPurposeRegister()
                LDR(val, [src], 4)
                ADD(val, val, 1)
                STR(val, [dst], 4)
                SUBS(length, 4)
                BNE(loop.begin)

            RETURN()

        assembly = f.assembly
        self.assertIn("AREA", assembly)
        self.assertIn("PROC", assembly)
        self.assertIn("ENDP", assembly)
        self.assertIn("EXPORT", assembly)

    def test_cortex_m35p_gas_assembly(self):
        """Cortex-M35P emits armv8-m.main (same ISA as M33)."""
        src_arg = Argument(ptr(const_uint32_t))
        dst_arg = Argument(ptr(uint32_t))
        len_arg = Argument(size_t)

        with Function("process", (src_arg, dst_arg, len_arg),
                      target=Microarchitecture.CortexM35P,
                      abi=arm_gnueabihf,
                      assembly_format=AssemblyFormat.GAS,
                      report_generation=False) as f:
            (src, dst, length) = LOAD.ARGUMENTS()

            with Loop() as loop:
                val = GeneralPurposeRegister()
                LDR(val, [src], 4)
                STR(val, [dst], 4)
                SUBS(length, 4)
                BNE(loop.begin)

            RETURN()

        assembly = f.assembly
        self.assertIn(".arch armv8-m.main", assembly)

    def test_cortex_m33_stack_alignment_validated(self):
        """Stack alignment check also applies to ARMv8-M.main (AAPCS requirement)."""
        from nervapy.arm.pseudo import IMPORT
        from nervapy.arm.registers import r4, r5, lr

        with self.assertRaises(ValueError) as ctx:
            with Function("misaligned_m33", (), None,
                          target=Microarchitecture.CortexM33,
                          abi=arm_gnueabihf,
                          assembly_format=AssemblyFormat.GAS,
                          report_generation=False) as f:
                ext_fn = IMPORT.FUNCTION("some_func")
                # Prologue adds PUSH {r3, r4} = 8 bytes (aligned)
                # This adds 4 more bytes making +12 total (misaligned)
                PUSH((r4,))
                BL(ext_fn)
                POP((r4,))
                BX(lr)

        self.assertIn("not 8-byte aligned", str(ctx.exception))

    def test_cortex_m33_aligned_bl_accepted(self):
        """Properly aligned stack before BL is accepted on Cortex-M33."""
        from nervapy.arm.pseudo import IMPORT
        from nervapy.arm.registers import r4, r5, lr

        with Function("aligned_m33", (), None,
                      target=Microarchitecture.CortexM33,
                      abi=arm_gnueabihf,
                      assembly_format=AssemblyFormat.GAS,
                      report_generation=False) as f:
            ext_fn = IMPORT.FUNCTION("helper_func")
            # Prologue adds PUSH {r3, r4} = 8 bytes; adding 8 more = aligned
            PUSH((r4, r5))
            BL(ext_fn)
            POP((r4, r5))
            BX(lr)

        assembly = f.assembly
        self.assertIn(".arch armv8-m.main", assembly)


class TestARMv8_1MMain(unittest.TestCase):
    """Tests for ARMv8.1-M.main (Cortex-M55, Cortex-M85)."""

    def test_cortex_m55_gas_assembly(self):
        """Cortex-M55 emits armv8.1-m.main arch directive."""
        src_arg = Argument(ptr(const_uint32_t))
        dst_arg = Argument(ptr(uint32_t))
        len_arg = Argument(size_t)

        with Function("m55_process", (src_arg, dst_arg, len_arg),
                      target=Microarchitecture.CortexM55,
                      abi=arm_gnueabihf,
                      assembly_format=AssemblyFormat.GAS,
                      report_generation=False) as f:
            (src, dst, length) = LOAD.ARGUMENTS()

            with Loop() as loop:
                val = GeneralPurposeRegister()
                LDR(val, [src], 4)
                ADD(val, val, 1)
                STR(val, [dst], 4)
                SUBS(length, 4)
                BNE(loop.begin)

            RETURN()

        assembly = f.assembly
        self.assertIn(".arch armv8.1-m.main", assembly)

    def test_cortex_m85_gas_assembly(self):
        """Cortex-M85 emits armv8.1-m.main arch directive."""
        src_arg = Argument(ptr(const_uint32_t))
        dst_arg = Argument(ptr(uint32_t))
        len_arg = Argument(size_t)

        with Function("m85_process", (src_arg, dst_arg, len_arg),
                      target=Microarchitecture.CortexM85,
                      abi=arm_gnueabihf,
                      assembly_format=AssemblyFormat.GAS,
                      report_generation=False) as f:
            (src, dst, length) = LOAD.ARGUMENTS()

            with Loop() as loop:
                val = GeneralPurposeRegister()
                LDR(val, [src], 4)
                ADD(val, val, 1)
                STR(val, [dst], 4)
                SUBS(length, 4)
                BNE(loop.begin)

            RETURN()

        assembly = f.assembly
        self.assertIn(".arch armv8.1-m.main", assembly)


class TestARMv8MSecurityInstructions(unittest.TestCase):
    """Tests for ARMv8-M TrustZone security instructions."""

    def test_sg_in_m33_function(self):
        """SG instruction is emitted in Cortex-M33 function."""
        # SG takes no operands - test that it is accepted on TrustZone target
        # and emitted in the assembly
        result_arg = Argument(ptr(uint32_t))

        with Function("secure_entry", (result_arg,),
                      target=Microarchitecture.CortexM33,
                      abi=arm_gnueabihf,
                      assembly_format=AssemblyFormat.GAS,
                      report_generation=False) as f:
            (result,) = LOAD.ARGUMENTS()
            SG()
            val = GeneralPurposeRegister()
            MOV(val, 42)
            STR(val, [result])
            RETURN()

        assembly = f.assembly
        self.assertIn("SG", assembly)
        self.assertIn(".arch armv8-m.main", assembly)

    def test_sg_in_m23_function(self):
        """SG instruction is accepted on Cortex-M23 (ARMv8-M.base with TrustZone)."""
        result_arg = Argument(ptr(uint32_t))

        with Function("secure_entry_m23", (result_arg,),
                      target=Microarchitecture.CortexM23,
                      abi=arm_gnueabihf,
                      assembly_format=AssemblyFormat.GAS,
                      report_generation=False) as f:
            (result,) = LOAD.ARGUMENTS()
            SG()
            val = GeneralPurposeRegister()
            MOV(val, 0)
            STR(val, [result])
            RETURN()

        assembly = f.assembly
        self.assertIn("SG", assembly)
        self.assertIn(".arch armv8-m.base", assembly)

    def test_sg_rejected_on_non_trustzone_target(self):
        """SG raises ValueError on a target without TrustZone (e.g. Cortex-M7)."""
        result_arg = Argument(ptr(uint32_t))

        with self.assertRaises(ValueError):
            with Function("no_trustzone", (result_arg,),
                          target=Microarchitecture.CortexM7,
                          abi=arm_gnueabihf,
                          assembly_format=AssemblyFormat.GAS,
                          report_generation=False) as f:
                (result,) = LOAD.ARGUMENTS()
                SG()
                RETURN()

    def test_bxns_in_m33_function(self):
        """BXNS instruction is emitted in Cortex-M33 function."""
        from nervapy.arm.registers import lr

        with Function("secure_return", (), None,
                      target=Microarchitecture.CortexM33,
                      abi=arm_gnueabihf,
                      assembly_format=AssemblyFormat.GAS,
                      report_generation=False) as f:
            SG()
            # Return to non-secure caller via BXNS lr
            BXNS(lr)

        assembly = f.assembly
        self.assertIn("BXNS", assembly)

    def test_tt_instruction_in_m33(self):
        """TT instruction queries address attributes on Cortex-M33."""
        addr_arg = Argument(ptr(uint32_t))
        result_arg = Argument(ptr(uint32_t))

        with Function("query_addr", (addr_arg, result_arg),
                      target=Microarchitecture.CortexM33,
                      abi=arm_gnueabihf,
                      assembly_format=AssemblyFormat.GAS,
                      report_generation=False) as f:
            (addr, result) = LOAD.ARGUMENTS()
            attr = GeneralPurposeRegister()
            TT(attr, addr)
            STR(attr, [result])
            RETURN()

        assembly = f.assembly
        self.assertIn("TT", assembly)

    def test_blxns_in_m33_function(self):
        """BLXNS instruction is accepted on Cortex-M33."""
        fn_ptr_arg = Argument(ptr(uint32_t))

        with Function("call_nonsecure", (fn_ptr_arg,),
                      target=Microarchitecture.CortexM33,
                      abi=arm_gnueabihf,
                      assembly_format=AssemblyFormat.GAS,
                      report_generation=False) as f:
            (fn_ptr,) = LOAD.ARGUMENTS()
            BLXNS(fn_ptr)
            RETURN()

        assembly = f.assembly
        self.assertIn("BLXNS", assembly)

    def test_tt_variants_in_m33(self):
        """TTA, TTT, TTAT instructions are accepted on Cortex-M33."""
        addr_arg = Argument(ptr(uint32_t))
        result_arg = Argument(ptr(uint32_t))

        with Function("query_all_tt", (addr_arg, result_arg),
                      target=Microarchitecture.CortexM33,
                      abi=arm_gnueabihf,
                      assembly_format=AssemblyFormat.GAS,
                      report_generation=False) as f:
            (addr, result) = LOAD.ARGUMENTS()
            attr = GeneralPurposeRegister()
            TTA(attr, addr)
            TTT(attr, addr)
            TTAT(attr, addr)
            STR(attr, [result])
            RETURN()

        assembly = f.assembly
        self.assertIn("TTA", assembly)
        self.assertIn("TTT", assembly)
        self.assertIn("TTAT", assembly)


class TestARMv8MExtensions(unittest.TestCase):
    """Tests for ARMv8-M extension detection."""

    def test_v8mbase_in_m23_extensions(self):
        """Cortex-M23 target has V8MBase in its extensions."""
        from nervapy.arm.isa import Extension
        target = Microarchitecture.CortexM23
        self.assertIn(Extension.V8MBase, target.extensions)
        self.assertIn(Extension.TrustZone, target.extensions)

    def test_v8mmain_in_m33_extensions(self):
        """Cortex-M33 target has V8MMain (and V7M via prerequisites) in extensions."""
        from nervapy.arm.isa import Extension
        target = Microarchitecture.CortexM33
        self.assertIn(Extension.V8MMain, target.extensions)
        self.assertIn(Extension.V7M, target.extensions)
        self.assertIn(Extension.DSP, target.extensions)
        self.assertIn(Extension.VFP4, target.extensions)
        self.assertIn(Extension.TrustZone, target.extensions)

    def test_v8_1mmain_in_m55_extensions(self):
        """Cortex-M55 target has V8_1MMain and MVE extensions."""
        from nervapy.arm.isa import Extension
        target = Microarchitecture.CortexM55
        self.assertIn(Extension.V8_1MMain, target.extensions)
        self.assertIn(Extension.V8MMain, target.extensions)
        self.assertIn(Extension.MVE, target.extensions)
        self.assertIn(Extension.TrustZone, target.extensions)

    def test_v8mmain_not_in_m7_extensions(self):
        """Cortex-M7 target does not have V8MMain."""
        from nervapy.arm.isa import Extension
        target = Microarchitecture.CortexM7
        self.assertNotIn(Extension.V8MMain, target.extensions)
        self.assertNotIn(Extension.V8MBase, target.extensions)
        self.assertNotIn(Extension.TrustZone, target.extensions)

    def test_m23_not_full_thumb2(self):
        """Cortex-M23 (ARMv8-M.base) does not have V7M."""
        from nervapy.arm.isa import Extension
        target = Microarchitecture.CortexM23
        self.assertNotIn(Extension.V7M, target.extensions)


if __name__ == '__main__':
    unittest.main()
