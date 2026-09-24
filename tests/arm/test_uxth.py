import unittest

from nervapy import *
from nervapy.arm import *
from nervapy.arm.abi import arm_gnueabihf
from nervapy.arm.microarchitecture import Microarchitecture


class TestUXTH(unittest.TestCase):
    def test_emits_zero_extend_halfword(self):
        with Function(
            "zero_extend_halfword",
            (),
            target=Microarchitecture.ARM11,
            abi=arm_gnueabihf,
            report_generation=False,
        ) as function:
            UXTH(r0, r1)
            RETURN()

        self.assertIn("UXTH r0, r1", function.assembly)

    def test_requires_armv6(self):
        with self.assertRaisesRegex(ValueError, "not supported"):
            with Function(
                "unsupported_uxth",
                (),
                target=Microarchitecture.ARM9,
                abi=arm_gnueabihf,
                report_generation=False,
            ):
                UXTH(r0, r1)

    def test_rejects_non_register_operands(self):
        with self.assertRaisesRegex(ValueError, "general-purpose registers"):
            with Function(
                "invalid_uxth",
                (),
                target=Microarchitecture.ARM11,
                abi=arm_gnueabihf,
                report_generation=False,
            ):
                UXTH(r0, 1)
