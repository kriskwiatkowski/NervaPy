import unittest

from nervapy import *
from nervapy.arm import *
from nervapy.arm.abi import arm_gnueabihf
from nervapy.arm.formats import AssemblyFormat
from nervapy.arm.microarchitecture import Microarchitecture
from nervapy.writer import ArmAssemblyWriter


def _make_function(name, assembly_format, target=Microarchitecture.CortexM33, **function_kwargs):
    function_kwargs.setdefault('is_thumb', True)
    with Function(name, (), None,
                  target=target, abi=arm_gnueabihf,
                  assembly_format=assembly_format,
                  report_generation=False, **function_kwargs) as f:
        PUSH((r4,))
        with Loop() as loop:
            SUBS(r4, 1)
            BNE(loop.begin)
        POP((r4,))
        BX(lr)
    return f


class TestArmAssemblyWriterGas(unittest.TestCase):
    """ArmAssemblyWriter packs several GAS functions behind one shared preamble,
    relying on generate_assembly(emit_file_preamble=False, emit_entry_label=False)
    rather than string-matching each function's ENTRY label out of its output."""

    def test_shared_preamble_and_no_duplicate_entry_labels(self):
        w = ArmAssemblyWriter(None, assembly_format=AssemblyFormat.GAS)
        w.add_function(_make_function('first', AssemblyFormat.GAS))
        w.add_function(_make_function('second', AssemblyFormat.GAS))
        out = w.serialize()

        self.assertEqual(out.count('.syntax unified'), 1)
        self.assertEqual(out.count('\t.text'), 1)
        self.assertNotIn('Lfirst.ENTRY:', out)
        self.assertNotIn('Lsecond.ENTRY:', out)
        # Each function's own (non-ENTRY) label must still be present.
        self.assertIn('Lfirst.', out)
        self.assertIn('Lsecond.', out)
        self.assertIn('first:', out)
        self.assertIn('second:', out)
        # Both functions keep their own .global export directive.
        self.assertIn('.global first', out)
        self.assertIn('.global second', out)

    def test_differing_alignment_is_tolerated_with_per_function_align(self):
        # GAS emits ".align N" inside each function body (not just the shared
        # preamble), so functions with different alignment requirements can
        # coexist in one GAS file without any aggregation.
        w = ArmAssemblyWriter(None, assembly_format=AssemblyFormat.GAS)
        w.add_function(_make_function('first', AssemblyFormat.GAS, alignment=2))
        w.add_function(_make_function('second', AssemblyFormat.GAS, alignment=8))
        out = w.serialize()

        self.assertIn('.align 2', out)
        self.assertIn('.align 8', out)

    def test_mismatched_thumb_mode_is_rejected(self):
        w = ArmAssemblyWriter(None, assembly_format=AssemblyFormat.GAS)
        w.add_function(_make_function('first', AssemblyFormat.GAS, is_thumb=True))
        with self.assertRaises(ValueError):
            w.add_function(_make_function('second', AssemblyFormat.GAS, is_thumb=False))

    def test_function_format_mismatching_writer_format_is_rejected(self):
        # generate_assembly() dispatches on the *function's* own
        # assembly_format, not the writer's, so adding an ARMCC function to a
        # GAS writer would otherwise silently mix PROC/ENDP syntax into GAS.
        w = ArmAssemblyWriter(None, assembly_format=AssemblyFormat.GAS)
        with self.assertRaises(ValueError):
            w.add_function(_make_function('first', AssemblyFormat.ARMCC))

    def test_mismatched_arch_is_rejected(self):
        # CortexM33 (ARMv8-M) and CortexM4 (ARMv7-M) produce different
        # gnu_arch_spec strings, so packing both must raise rather than
        # silently assemble the second function under the first's .arch.
        w = ArmAssemblyWriter(None, assembly_format=AssemblyFormat.GAS)
        w.add_function(_make_function('first', AssemblyFormat.GAS, target=Microarchitecture.CortexM33))
        with self.assertRaises(ValueError):
            w.add_function(_make_function('second', AssemblyFormat.GAS, target=Microarchitecture.CortexM4))


class TestArmAssemblyWriterArmcc(unittest.TestCase):
    """Same packing behavior for ARMCC, where a stray extra END would otherwise
    truncate everything written after the first function."""

    def test_shared_preamble_single_end_and_no_duplicate_entry_labels(self):
        w = ArmAssemblyWriter(None, assembly_format=AssemblyFormat.ARMCC)
        w.add_function(_make_function('first', AssemblyFormat.ARMCC))
        w.add_function(_make_function('second', AssemblyFormat.ARMCC))
        out = w.serialize()

        self.assertEqual(out.count('AREA    ||.text||'), 1)
        end_lines = [line for line in out.splitlines() if line == '        END']
        self.assertEqual(len(end_lines), 1)
        self.assertEqual(out.count('        ENDP'), 2)  # one per function body
        self.assertNotIn('first_ENTRY', out)
        self.assertNotIn('second_ENTRY', out)
        self.assertIn('first_', out)
        self.assertIn('second_', out)
        self.assertIn('first    PROC', out)
        self.assertIn('second    PROC', out)

    def test_area_alignment_is_max_of_all_packed_functions_regardless_of_order(self):
        w = ArmAssemblyWriter(None, assembly_format=AssemblyFormat.ARMCC)
        w.add_function(_make_function('first', AssemblyFormat.ARMCC, alignment=2))
        w.add_function(_make_function('second', AssemblyFormat.ARMCC, alignment=4))
        out = w.serialize()

        self.assertIn('AREA    ||.text||, CODE, READONLY, ALIGN=4', out)

    def test_mismatched_thumb_mode_is_rejected(self):
        w = ArmAssemblyWriter(None, assembly_format=AssemblyFormat.ARMCC)
        w.add_function(_make_function('first', AssemblyFormat.ARMCC, is_thumb=True))
        with self.assertRaises(ValueError):
            w.add_function(_make_function('second', AssemblyFormat.ARMCC, is_thumb=False))

    def test_custom_file_preamble_does_not_get_auto_end(self):
        w = ArmAssemblyWriter(None, assembly_format=AssemblyFormat.ARMCC,
                               file_preamble="        AREA    ||my.text||, CODE, READONLY")
        w.add_function(_make_function('first', AssemblyFormat.ARMCC))
        out = w.serialize()

        self.assertNotIn('        END', out.splitlines())

    def test_mismatched_fpu_spec_is_rejected(self):
        # CortexM4 requires VFPv4 (armcc_fpu_spec is set); CortexM33 has no
        # FPU extension (armcc_fpu_spec is None). ARMCC expresses the FPU
        # requirement only once, file-level, so this must raise rather than
        # silently drop the second function's FPU requirement.
        w = ArmAssemblyWriter(None, assembly_format=AssemblyFormat.ARMCC)
        w.add_function(_make_function('first', AssemblyFormat.ARMCC, target=Microarchitecture.CortexM4))
        with self.assertRaises(ValueError):
            w.add_function(_make_function('second', AssemblyFormat.ARMCC, target=Microarchitecture.CortexM33))

    def test_mismatched_preserve8_is_rejected(self):
        w = ArmAssemblyWriter(None, assembly_format=AssemblyFormat.ARMCC)
        w.add_function(_make_function('first', AssemblyFormat.ARMCC, preserve8=True))
        with self.assertRaises(ValueError):
            w.add_function(_make_function('second', AssemblyFormat.ARMCC, preserve8=False))

    def test_gas_function_rejected_by_armcc_writer(self):
        w = ArmAssemblyWriter(None, assembly_format=AssemblyFormat.ARMCC)
        with self.assertRaises(ValueError):
            w.add_function(_make_function('first', AssemblyFormat.GAS))

    def test_explicit_none_output_path_does_not_crash(self):
        # ArmAssemblyWriter is routinely used purely in-memory, via
        # serialize(), with no file ever opened -- output_path=None must work.
        w = ArmAssemblyWriter(None, assembly_format=AssemblyFormat.ARMCC)
        w.add_function(_make_function('first', AssemblyFormat.ARMCC))
        w.add_function(_make_function('second', AssemblyFormat.ARMCC))
        out = w.serialize()

        self.assertIn('first    PROC', out)
        self.assertIn('second    PROC', out)


if __name__ == '__main__':
    unittest.main()
