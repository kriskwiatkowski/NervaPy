# This file is part of NervaPy package and is licensed under the Simplified BSD license.
#    See license.rst for the full text of the license.

__version_info__ = (0, 2, 0)
__version__ = '.'.join(map(str, __version_info__))

from nervapy.c.types import (Float16, Float32, Float64, Type, Yep8s, Yep8u,
                             Yep16f, Yep16s, Yep16u, Yep32f, Yep32s, Yep32u,
                             Yep64f, Yep64s, Yep64u, YepSize, char, const_char,
                             const_double_, const_Float16, const_Float32,
                             const_Float64, const_float_, const_int8_t,
                             const_int16_t, const_int32_t, const_int64_t,
                             const_intptr_t, const_ptr, const_ptrdiff_t,
                             const_signed_char, const_signed_int,
                             const_signed_long, const_signed_long_long,
                             const_signed_short, const_size_t, const_uint8_t,
                             const_uint16_t, const_uint32_t, const_uint64_t,
                             const_uintptr_t, const_unsigned_char,
                             const_unsigned_int, const_unsigned_long,
                             const_unsigned_long_long, const_unsigned_short,
                             const_wchar_t, const_Yep8s, const_Yep8u,
                             const_Yep16f, const_Yep16s, const_Yep16u,
                             const_Yep32f, const_Yep32s, const_Yep32u,
                             const_Yep64f, const_Yep64s, const_Yep64u,
                             const_YepSize, double_, float_, int8_t, int16_t,
                             int32_t, int64_t, intptr_t, ptr, ptrdiff_t,
                             signed_char, signed_int, signed_long,
                             signed_long_long, signed_short, size_t, uint8_t,
                             uint16_t, uint32_t, uint64_t, uintptr_t,
                             unsigned_char, unsigned_int, unsigned_long,
                             unsigned_long_long, unsigned_short, wchar_t)
from nervapy.function import Argument
from nervapy.literal import Constant
from nervapy.stream import InstructionStream


class ConstantBucket:
    def __init__(self, capacity):
        self.capacity = capacity
        self.constants = []
    
    def add(self, constant):
        self.constants.append(constant)
    
    def is_full(self):
        return False  # Simple implementation for now


class RegisterAllocationError(Exception):
    pass
