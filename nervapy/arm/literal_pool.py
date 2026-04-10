"""
Literal Pool Support for ARM Assembly

This module implements literal pool functionality for the LDR =label pseudo-instruction.
It manages constant literals that can be loaded into registers using PC-relative addressing.

Usage:
    from nervapy.arm.literal_pool import Literal
    from nervapy.arm.generic import LDR
    
    with Function("my_func", ...) as func:
        # Load constant using literal pool
        LDR(r0, literal=Literal(0x11111111))
        
        # Load with custom label
        LDR(r0, literal=Literal(0x11111111, label="MY_CONSTANT"))
        
        # Or load from ConstantData label
        magic = ConstantData.uint32(0x11111111, name="MAGIC_NUMBER")
        LDR(r0, literal=magic)
"""

import inspect

import nervapy.arm.function
import nervapy.stream
from nervapy.arm.generic import Operand
from nervapy.arm.instructions import Instruction


class Literal:
    """
    Wrapper class for literal values with optional custom labels.
    
    Use this class to specify a literal value for LDR instruction with an optional label.
    This is useful when you want to control the label name in the generated assembly.
    
    Examples:
        # Simple literal (auto-generated label)
        LDR(r0, literal=Literal(0x11111111))
        # Generates: literal_123456789: .word 0x11111111
        
        # Literal with custom label
        LDR(r0, literal=Literal(0x11111111, label="MY_CONSTANT"))
        # Generates: MY_CONSTANT: .word 0x11111111
        
        # 64-bit literal
        LDR(r0, literal=Literal(0x123456789ABCDEF0))
        
        # Direct integer also works (backward compatibility)
        LDR(r1, literal=0x22222222)
    """
    
    def __init__(self, value, label=None):
        """
        Args:
            value: The literal value (int or float)
            label: Optional custom label name for the literal
        """
        self.value = value
        self.label = label
    
    def get_value(self):
        """Return the literal value"""
        return self.value
    
    def get_label(self):
        """Return the custom label, if any"""
        return self.label


class LiteralPoolEntry:
    """Represents a single entry in the literal pool"""
    
    def __init__(self, value, label=None, size=32):
        """
        Args:
            value: The literal value (int, float, or ConstantData)
            label: Optional label name for the literal
            size: Size in bits (8, 16, 32, or 64)
        """
        self.value = value
        self.label = label or f"literal_{id(self)}"
        self.size = size
        self._is_constant_data = False
        
        # Check if value is a ConstantData object
        try:
            from nervapy.constant_data import ConstantData
            if isinstance(value, ConstantData):
                self._is_constant_data = True
                self.label = value.get_label()
        except ImportError:
            pass
    
    def is_constant_data(self):
        """Check if this entry references ConstantData"""
        return self._is_constant_data
    
    def get_label(self):
        """Get the label for this literal"""
        return self.label
    
    def get_value(self):
        """Get the numeric value"""
        if self._is_constant_data:
            # For ConstantData, return the first value
            if hasattr(self.value, 'data') and len(self.value.data) > 0:
                return self.value.data[0]
            return 0
        return self.value
    
    def generate_assembly(self, format='gas'):
        """Generate assembly for this literal entry"""
        if self._is_constant_data:
            # ConstantData generates its own .data section
            return ""
        
        if format == 'gas':
            if self.size == 64:
                # 64-bit value
                return f"{self.label}:\n\t.word 0x{self.value & 0xFFFFFFFF:08X}, 0x{(self.value >> 32) & 0xFFFFFFFF:08X}"
            elif self.size == 32:
                return f"{self.label}:\n\t.word 0x{self.value:08X}"
            elif self.size == 16:
                return f"{self.label}:\n\t.hword 0x{self.value:04X}"
            elif self.size == 8:
                return f"{self.label}:\n\t.byte 0x{self.value:02X}"
        elif format == 'armcc':
            if self.size == 64:
                return f"{self.label}    DCD    0x{self.value & 0xFFFFFFFF:08X}, 0x{(self.value >> 32) & 0xFFFFFFFF:08X}"
            elif self.size == 32:
                return f"{self.label}    DCD    0x{self.value:08X}"
            elif self.size == 16:
                return f"{self.label}    DCW    0x{self.value:04X}"
            elif self.size == 8:
                return f"{self.label}    DCB    0x{self.value:02X}"
        
        return ""


class LiteralPool:
    """Manages a pool of literals for a function"""
    
    def __init__(self):
        self.entries = []
        self._value_map = {}  # Map values to entries for deduplication
    
    def add_literal(self, value, label=None, size=32):
        """
        Add a literal to the pool
        
        Args:
            value: The literal value
            label: Optional label name
            size: Size in bits
            
        Returns:
            LiteralPoolEntry: The pool entry
        """
        # Check if we already have this value (deduplication)
        if label is None and not self._is_constant_data(value):
            key = (value, size)
            if key in self._value_map:
                return self._value_map[key]
        
        entry = LiteralPoolEntry(value, label, size)
        self.entries.append(entry)
        
        if label is None and not entry.is_constant_data():
            self._value_map[(value, size)] = entry
        
        return entry
    
    def _is_constant_data(self, value):
        """Check if value is ConstantData"""
        try:
            from nervapy.constant_data import ConstantData
            return isinstance(value, ConstantData)
        except ImportError:
            return False
    
    def generate_assembly(self, format='gas'):
        """Generate assembly for the entire literal pool"""
        if not self.entries:
            return ""
        
        lines = []
        
        if format == 'gas':
            lines.append("\t.align 4")
            for entry in self.entries:
                if not entry.is_constant_data():
                    asm = entry.generate_assembly(format='gas')
                    if asm:
                        lines.append(asm)
        elif format == 'armcc':
            lines.append("        ALIGN 4")
            for entry in self.entries:
                if not entry.is_constant_data():
                    asm = entry.generate_assembly(format='armcc')
                    if asm:
                        lines.append(asm)
        
        return "\n".join(lines) if lines else ""


class LiteralLoadInstruction(Instruction):
    """
    LDR pseudo-instruction for loading literals: LDR rd, =value
    
    This generates either:
    1. A literal pool entry + PC-relative LDR
    2. An optimized MOV/MVN if the value is encodable
    3. A reference to a ConstantData label
    """
    
    def __init__(self, register, value, label=None, origin=None):
        """
        Args:
            register: Destination register
            value: Literal value (int, float, ConstantData, or Literal object)
            label: Optional custom label name for the literal
        """
        self.literal_register = Operand(register)
        
        # Extract value and label from Literal object if provided
        actual_value = value
        actual_label = label
        
        if isinstance(value, Literal):
            actual_value = value.get_value()
            if label is None:  # Only use Literal's label if not explicitly provided
                actual_label = value.get_label()
        
        self.literal_value = actual_value
        self.pool_entry = None
        
        # Check if it's a ConstantData object
        self._is_constant_data = False
        try:
            from nervapy.constant_data import ConstantData
            if isinstance(actual_value, ConstantData):
                self._is_constant_data = True
        except ImportError:
            pass
        
        # Add to literal pool if function is active
        if nervapy.arm.function.active_function is not None:
            if not hasattr(nervapy.arm.function.active_function, 'literal_pool'):
                nervapy.arm.function.active_function.literal_pool = LiteralPool()
            
            size = 32
            if isinstance(actual_value, int):
                if actual_value > 0xFFFFFFFF:
                    size = 64
            
            self.pool_entry = nervapy.arm.function.active_function.literal_pool.add_literal(
                actual_value, label=actual_label, size=size
            )
        
        # Create instruction representation
        super(LiteralLoadInstruction, self).__init__(
            "LDR", [self.literal_register], origin=origin
        )
    
    def __str__(self):
        """Generate the assembly string"""
        if self.pool_entry:
            label = self.pool_entry.get_label()
            return f"LDR {self.literal_register}, ={label}"
        else:
            # Fallback if no pool entry
            return f"LDR {self.literal_register}, =0x{self.literal_value:X}"
    
    def get_output_registers_list(self):
        """Return list of registers modified by this instruction"""
        return [self.literal_register.get_registers_list()[0]]
    
    def get_input_registers_list(self):
        """Return list of registers used by this instruction"""
        return []


def LDR_LITERAL(register, value, label=None):
    """
    Load a literal value into a register using the literal pool.
    
    This implements the ARM pseudo-instruction: LDR rd, =value
    
    Args:
        register: Destination general-purpose register
        value: Literal value to load (int, float, or ConstantData)
        label: Optional custom label name for the literal
        
    Returns:
        LiteralLoadInstruction: The instruction object
        
    Examples:
        # Load a 32-bit constant
        LDR_LITERAL(r0, 0x11111111)
        
        # Load with custom label
        LDR_LITERAL(r0, 0x11111111, label="my_constant")
        
        # Load from ConstantData
        magic = ConstantData.uint32(0x12345678, name="MAGIC")
        LDR_LITERAL(r1, magic)
        
        # Load a large value
        LDR_LITERAL(r2, 0xDEADBEEF)
    
    Note:
        The assembler will automatically:
        - Create a literal pool entry
        - Generate PC-relative LDR instruction
        - Place the literal in .text or .rodata section
        
        For ConstantData objects, it references the .data section label.
    """
    origin = (
        inspect.stack() if nervapy.arm.function.active_function.collect_origin else None
    )
    instruction = LiteralLoadInstruction(register, value, label=label, origin=origin)
    if nervapy.stream.active_stream is not None:
        nervapy.stream.active_stream.add_instruction(instruction)
    return instruction


# Alias for convenience
LDRL = LDR_LITERAL
