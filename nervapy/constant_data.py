"""
ConstantData - Extended Constant class that generates .data sections

This module provides ConstantData class that automatically:
1. Creates a Constant with metadata
2. Registers itself with the active Function
3. Generates .data section entries
4. Provides a label/address for use with LDR instructions

Usage:
    from nervapy.constant_data import ConstantData
    
    with Function("my_func", ...) as func:
        # Create constant data - automatically added to function
        magic = ConstantData.uint32(0x11111111, name="magic_number")
        
        # Use with LDR (label will be generated)
        # Note: You'll need to use raw assembly for LDR =label
        # Or manually construct the address loading
        
    # Assembly will include .data section automatically
    print(func.assembly)
"""

from nervapy.literal import Constant


class ConstantData(Constant):
    """Extended Constant that registers with Function for .data generation"""

    # Class-level registry of constants per function
    _function_constants: dict[int, list["ConstantData"]] = {}

    def __init__(self, size, repeats, data, element_ctype, name):
        super().__init__(size, repeats, data, element_ctype, name)

        # Register with active function
        self._register_with_function()

    def _register_with_function(self):
        """Register this constant with the active function"""
        from nervapy.arm.function import active_function

        if active_function is not None:
            func_id = id(active_function)
            if func_id not in ConstantData._function_constants:
                ConstantData._function_constants[func_id] = []
            ConstantData._function_constants[func_id].append(self)

    def get_label(self):
        """Return the label name for this constant"""
        if self.name and len(self.name) > 0:
            if hasattr(self.name[0], 'name'):
                return self.name[0].name
            return str(self.name[0])
        return f"const_{id(self)}"

    def generate_data_section(self):
        """Generate .data section assembly for this constant"""
        lines = []
        label = self.get_label()
        lines.append(f"\t.global {label}")
        lines.append(f"\t.type {label}, %object")
        lines.append(f"{label}:")

        # Determine word size based on element type
        from nervapy.c.types import int64_t, uint64_t

        if self.element_ctype in [uint64_t, int64_t]:
            # 64-bit values - use .quad or two .word directives
            if self.repeats == 1:
                # Single 64-bit value - split into two 32-bit words (little-endian)
                low = self.data[0] & 0xFFFFFFFF
                high = (self.data[0] >> 32) & 0xFFFFFFFF
                lines.append(f"\t.word 0x{low:08X}, 0x{high:08X}")
            else:
                # Multiple 64-bit values
                words = []
                for val in self.data:
                    low = val & 0xFFFFFFFF
                    high = (val >> 32) & 0xFFFFFFFF
                    words.extend([f"0x{low:08X}", f"0x{high:08X}"])
                lines.append(f"\t.word {', '.join(words)}")
        else:
            # 32-bit or smaller values
            if self.repeats == 1:
                lines.append(f"\t.word 0x{self.data[0]:08X}")
            else:
                words = ", ".join(f"0x{v:08X}" for v in self.data)
                lines.append(f"\t.word {words}")

        return "\n".join(lines)

    @staticmethod
    def get_function_constants(function):
        """Get all constants registered with a function"""
        func_id = id(function)
        return ConstantData._function_constants.get(func_id, [])

    @staticmethod
    def clear_function_constants(function):
        """Clear constants for a function (called after generation)"""
        func_id = id(function)
        if func_id in ConstantData._function_constants:
            del ConstantData._function_constants[func_id]

    @staticmethod
    def generate_all_data_sections(function):
        """Generate complete .data section for all constants in a function"""
        constants = ConstantData.get_function_constants(function)
        if not constants:
            return ""

        lines = ["\n\t.data", "\t.align 4"]
        for const in constants:
            lines.append(const.generate_data_section())

        return "\n".join(lines) + "\n"

    # Factory methods (same as Constant but return ConstantData)

    @staticmethod
    def uint32(number, name=None):
        """Create a 32-bit unsigned integer constant with .data section"""
        from nervapy.name import Name
        from nervapy.parse import parse_assigned_variable_name
        from nervapy.util import is_int, is_int32

        if not is_int(number):
            raise TypeError(f"The value {number} is not an integer")
        if not is_int32(number):
            raise ValueError(f"The number {number} is not a 32-bit integer")

        if number < 0:
            number += 0x100000000

        if name is not None:
            Name.check_name(name)
            name_obj = Name(name=name)
        else:
            import inspect
            name_obj = Name(
                prename=parse_assigned_variable_name(inspect.stack(), "ConstantData.uint32")
            )

        from nervapy.c.types import uint32_t
        return ConstantData(4, 1, (number,), uint32_t, name_obj)

    @staticmethod
    def uint32x4(number1, number2=None, number3=None, number4=None, name=None):
        """Create a 4-element 32-bit unsigned integer array constant"""
        from nervapy.c.types import uint32_t
        from nervapy.name import Name
        from nervapy.parse import parse_assigned_variable_name
        from nervapy.util import is_int, is_int32

        args = [arg for arg in [number1, number2, number3, number4] if arg is not None]
        if len(args) == 0:
            raise ValueError("At least one constant value must be specified")
        if len(args) != 1 and len(args) != 4:
            raise ValueError("Either 1 or 4 values must be specified")

        for i, num in enumerate(args):
            if not is_int(num):
                raise TypeError(f"The value {num} is not an integer")
            if not is_int32(num):
                raise ValueError(f"The number {num} is not a 32-bit integer")
            if num < 0:
                args[i] += 0x100000000

        if len(args) == 1:
            args = [args[0]] * 4

        if name is not None:
            Name.check_name(name)
            name_obj = Name(name=name)
        else:
            import inspect
            name_obj = Name(
                prename=parse_assigned_variable_name(inspect.stack(), "ConstantData.uint32x4")
            )

        return ConstantData(16, 4, tuple(args), uint32_t, name_obj)

    @staticmethod
    def uint64(number, name=None):
        """Create a 64-bit unsigned integer constant with .data section"""
        from nervapy.c.types import uint64_t
        from nervapy.name import Name
        from nervapy.parse import parse_assigned_variable_name
        from nervapy.util import is_int, is_int64

        if not is_int(number):
            raise TypeError(f"The value {number} is not an integer")
        if not is_int64(number):
            raise ValueError(f"The number {number} is not a 64-bit integer")

        if number < 0:
            number += 0x10000000000000000

        if name is not None:
            Name.check_name(name)
            name_obj = Name(name=name)
        else:
            import inspect
            name_obj = Name(
                prename=parse_assigned_variable_name(inspect.stack(), "ConstantData.uint64")
            )

        return ConstantData(8, 1, (number,), uint64_t, name_obj)


# Note: Auto-patching is done when Function is imported via __init__.py
# For manual usage, call install_constant_data_support() after importing Function


def install_constant_data_support():
    """Install ConstantData support by patching the Function class
    
    This enables automatic .data section generation for ConstantData objects.
    Call this after importing Function but before creating any functions.
    
    Example:
        from nervapy import *
        from nervapy.arm import *
        from nervapy.constant_data import ConstantData, install_constant_data_support
        
        install_constant_data_support()  # Enable automatic .data sections
        
        with Function(...) as func:
            const = ConstantData.uint32(111, name="my_const")
            ...
    """
    from nervapy.arm.function import Function

    # Check if already patched
    if hasattr(Function, '_constant_data_patched'):
        return

    # Save original methods
    original_assembly = Function.assembly.fget
    original_exit = Function.__exit__

    def patched_assembly(self):
        """Patched assembly property that appends .data sections"""
        # Get original assembly
        asm = original_assembly(self)

        # Append .data section if there are constants
        # Note: We check for constants stored on the function instance
        # because they may have been cleared from the global registry
        if hasattr(self, '_constant_data_list'):
            constants = self._constant_data_list
        else:
            constants = ConstantData.get_function_constants(self)

        if constants:
            lines = ["\n\t.data", "\t.align 4"]
            for const in constants:
                lines.append(const.generate_data_section())
            asm += "\n".join(lines) + "\n"

        return asm

    def patched_exit(self, exc_type, exc_value, traceback):
        """Patched __exit__ that saves constants before cleanup"""
        # Save constants to function instance before clearing global registry
        self._constant_data_list = list(ConstantData.get_function_constants(self))

        # Call original __exit__
        result = original_exit(self, exc_type, exc_value, traceback)

        # Clear from global registry (but kept in _constant_data_list)
        ConstantData.clear_function_constants(self)

        return result

    # Apply patches
    Function.assembly = property(patched_assembly)
    Function.__exit__ = patched_exit
    Function._constant_data_patched = True

