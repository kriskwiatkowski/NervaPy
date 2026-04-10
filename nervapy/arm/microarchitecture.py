# This file is part of PeachPy package and is licensed under the Simplified BSD license.
#    See license.rst for the full text of the license.

from typing import Optional

from nervapy.arm.isa import Extension, Extensions


class Microarchitecture:
    def __init__(self, name, extensions):
        self.name = name
        self.extensions = Extensions(
            *[
                prerequisite
                for extension in extensions
                for prerequisite in extension.prerequisites
            ]
        )

    def is_supported(self, extension):
        return extension in self.extensions

    @property
    def id(self):
        return self.name.replace(" ", "")

    def __add__(self, extension):
        return Microarchitecture(self.name, self.extensions + extension)

    def __sub__(self, extension):
        return Microarchitecture(self.name, self.extensions - extension)

    def __str__(self):
        return self.name

    Default: Optional["Microarchitecture"] = None
    XScale: Optional["Microarchitecture"] = None
    ARM9: Optional["Microarchitecture"] = None
    ARM11: Optional["Microarchitecture"] = None
    CortexA5: Optional["Microarchitecture"] = None
    CortexA7: Optional["Microarchitecture"] = None
    CortexA8: Optional["Microarchitecture"] = None
    CortexA9: Optional["Microarchitecture"] = None
    CortexA12: Optional["Microarchitecture"] = None
    CortexA15: Optional["Microarchitecture"] = None
    CortexM0: Optional["Microarchitecture"] = None
    CortexM0Plus: Optional["Microarchitecture"] = None
    CortexM1: Optional["Microarchitecture"] = None
    CortexM3: Optional["Microarchitecture"] = None
    CortexM4: Optional["Microarchitecture"] = None
    CortexM7: Optional["Microarchitecture"] = None
    CortexM23: Optional["Microarchitecture"] = None
    CortexM33: Optional["Microarchitecture"] = None
    CortexM35P: Optional["Microarchitecture"] = None
    CortexM55: Optional["Microarchitecture"] = None
    CortexM85: Optional["Microarchitecture"] = None
    Scorpion: Optional["Microarchitecture"] = None
    Krait: Optional["Microarchitecture"] = None
    PJ4: Optional["Microarchitecture"] = None


Microarchitecture.Default = Microarchitecture("Default", Extension.All)
Microarchitecture.XScale = Microarchitecture(
    "XScale", [Extension.V5E, Extension.Thumb, Extension.XScale, Extension.WMMX2]
)
Microarchitecture.ARM9 = Microarchitecture("ARM9", [Extension.V5E, Extension.Thumb])
Microarchitecture.ARM11 = Microarchitecture(
    "ARM11", [Extension.V6K, Extension.Thumb, Extension.VFP2, Extension.VFPVectorMode]
)
Microarchitecture.CortexA5 = Microarchitecture(
    "Cortex A5",
    [
        Extension.V7MP,
        Extension.Thumb2,
        Extension.VFP4,
        Extension.VFPd32,
        Extension.NEON2,
    ],
)
Microarchitecture.CortexA7 = Microarchitecture(
    "Cortex A7",
    [
        Extension.V7MP,
        Extension.Thumb2,
        Extension.Div,
        Extension.VFP4,
        Extension.VFPd32,
        Extension.NEON2,
    ],
)
Microarchitecture.CortexA8 = Microarchitecture(
    "Cortex A8",
    [Extension.V7, Extension.Thumb2, Extension.VFP3, Extension.VFPd32, Extension.NEON],
)
Microarchitecture.CortexA9 = Microarchitecture(
    "Cortex A9", [Extension.V7MP, Extension.Thumb2, Extension.VFP3, Extension.VFPHP]
)
Microarchitecture.CortexA12 = Microarchitecture(
    "Cortex A12",
    [
        Extension.V7MP,
        Extension.Thumb2,
        Extension.Div,
        Extension.VFP4,
        Extension.VFPd32,
        Extension.NEON2,
    ],
)
Microarchitecture.CortexA15 = Microarchitecture(
    "Cortex A15",
    [
        Extension.V7MP,
        Extension.Thumb2,
        Extension.Div,
        Extension.VFP4,
        Extension.VFPd32,
        Extension.NEON2,
    ],
)
Microarchitecture.Scorpion = Microarchitecture(
    "Scorpion",
    [
        Extension.V7MP,
        Extension.Thumb2,
        Extension.VFP3,
        Extension.VFPd32,
        Extension.VFPHP,
        Extension.NEON,
        Extension.NEONHP,
    ],
)
Microarchitecture.Krait = Microarchitecture(
    "Krait",
    [
        Extension.V7MP,
        Extension.Thumb2,
        Extension.Div,
        Extension.VFP4,
        Extension.VFPd32,
        Extension.NEON2,
    ],
)
Microarchitecture.PJ4 = Microarchitecture(
    "PJ4", [Extension.V7, Extension.Thumb2, Extension.VFP3, Extension.WMMX2]
)

# Cortex-M series microarchitectures
Microarchitecture.CortexM0 = Microarchitecture(
    "Cortex M0", [Extension.V6, Extension.Thumb2]
)
Microarchitecture.CortexM0Plus = Microarchitecture(
    "Cortex M0+", [Extension.V6, Extension.Thumb2]
)
Microarchitecture.CortexM1 = Microarchitecture(
    "Cortex M1", [Extension.V6, Extension.Thumb2]
)
Microarchitecture.CortexM3 = Microarchitecture(
    "Cortex M3", [Extension.V7M, Extension.Thumb2]
)
Microarchitecture.CortexM4 = Microarchitecture(
    "Cortex M4", [Extension.V7M, Extension.Thumb2, Extension.DSP, Extension.VFP4]
)
Microarchitecture.CortexM7 = Microarchitecture(
    "Cortex M7",
    [Extension.V7M, Extension.Thumb2, Extension.DSP, Extension.VFP4, Extension.VFPd32],
)

# ARMv8-M Cortex-M series microarchitectures
Microarchitecture.CortexM23 = Microarchitecture(
    "Cortex M23", [Extension.V8MBase, Extension.Thumb, Extension.TrustZone]
)
Microarchitecture.CortexM33 = Microarchitecture(
    "Cortex M33",
    [
        Extension.V8MMain,
        Extension.Thumb2,
        Extension.DSP,
        Extension.TrustZone,
    ],
)
Microarchitecture.CortexM35P = Microarchitecture(
    "Cortex M35P",
    [
        Extension.V8MMain,
        Extension.Thumb2,
        Extension.DSP,
        Extension.TrustZone,
    ],
)
Microarchitecture.CortexM55 = Microarchitecture(
    "Cortex M55",
    [
        Extension.V8_1MMain,
        Extension.Thumb2,
        Extension.DSP,
        Extension.VFP4,
        Extension.TrustZone,
        Extension.MVE,
    ],
)
Microarchitecture.CortexM85 = Microarchitecture(
    "Cortex M85",
    [
        Extension.V8_1MMain,
        Extension.Thumb2,
        Extension.DSP,
        Extension.VFP4,
        Extension.TrustZone,
        Extension.MVE,
    ],
)
