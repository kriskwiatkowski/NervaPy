# ARM Shifted Register Addressing Mode

## Overview

NervaPy supports generating ARM load/store instructions with shifted register offsets. This addressing mode is particularly useful for efficient array access where elements are larger than 1 byte.

## Generating Instructions with Shifted Register Offsets

### Basic Usage

```python
from nervapy.arm.registers import r2, r5, r6, ShiftedGeneralPurposeRegister
from nervapy.arm.generic import LDR_W

# Create a shifted register: r5 << 2
shifted_r5 = ShiftedGeneralPurposeRegister(r5, 'LSL', 2)

# Generate: ldr.w r2, [r6, r5, lsl #2]
LDR_W(r2, [r6, shifted_r5])
```

### Supported Shift Types

| Shift Type | Description | Valid Range | Use Case |
|------------|-------------|-------------|----------|
| `LSL` | Logical Shift Left | 1-31 | Multiply index (array access) |
| `LSR` | Logical Shift Right | 1-32 | Divide unsigned index |
| `ASR` | Arithmetic Shift Right | 1-32 | Divide signed index (preserves sign) |
| `ROR` | Rotate Right | 1-31 | Bit rotation operations |
| `RRX` | Rotate Right Extended | N/A | Single-bit rotation with carry |

### Array Access Examples

#### 32-bit Integer Array (4 bytes per element)
```python
# array[index] where each element is 4 bytes
# Shift left by 2 to multiply index by 4
index_shifted = ShiftedGeneralPurposeRegister(r5, 'LSL', 2)
LDR_W(r2, [r6, index_shifted])  # ldr.w r2, [r6, r5, lsl #2]
```

#### 16-bit Short Array (2 bytes per element)
```python
# array[index] where each element is 2 bytes
# Shift left by 1 to multiply index by 2
index_shifted = ShiftedGeneralPurposeRegister(r5, 'LSL', 1)
LDRH_W(r2, [r6, index_shifted])  # ldrh.w r2, [r6, r5, lsl #1]
```

#### 64-bit Long Array (8 bytes per element)
```python
# array[index] where each element is 8 bytes
# Shift left by 3 to multiply index by 8
index_shifted = ShiftedGeneralPurposeRegister(r5, 'LSL', 3)
LDR_W(r2, [r6, index_shifted])  # ldr.w r2, [r6, r5, lsl #3]
```

### Supported Instructions

All word, halfword, and byte load/store instructions support shifted register addressing:

**Load Instructions:**
- `LDR_W` - Load word (32-bit)
- `LDRH_W` - Load halfword (16-bit)
- `LDRSH_W` - Load signed halfword
- `LDRB_W` - Load byte (8-bit)
- `LDRSB_W` - Load signed byte

**Store Instructions:**
- `STR_W` - Store word (32-bit)
- `STRH_W` - Store halfword (16-bit)
- `STRB_W` - Store byte (8-bit)

### Complete Example

```python
from nervapy.arm.registers import r0, r1, r2, ShiftedGeneralPurposeRegister
from nervapy.arm.generic import LDR_W, STR_W

# Access 32-bit array element
# C equivalent: value = array[index]
# where: r0 = array base address, r1 = index, r2 = value

index_times_4 = ShiftedGeneralPurposeRegister(r1, 'LSL', 2)

# Load: ldr.w r2, [r0, r1, lsl #2]
LDR_W(r2, [r0, index_times_4])

# Store: str.w r2, [r0, r1, lsl #2]
STR_W(r2, [r0, index_times_4])
```

## Implementation Details

The shifted register addressing mode is implemented through the `ShiftedGeneralPurposeRegister` class, which can be used as an offset in memory operands. The `LoadStoreInstruction` class automatically validates and supports this addressing mode for all applicable instruction variants.

When you pass a `ShiftedGeneralPurposeRegister` as the second element of a memory address list (e.g., `[base_register, shifted_register]`), NervaPy correctly interprets and generates the shifted register addressing syntax.

## See Also

- Example script: `examples/arm_ldr_shifted_register.py`
- ARM Architecture Reference Manual: Load/Store Instructions with Shifted Register Offset
