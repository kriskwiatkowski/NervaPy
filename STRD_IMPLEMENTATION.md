# STRD/LDRD Implementation Summary

## Overview
Successfully implemented the STRD (Store Register Dual) and LDRD (Load Register Dual) instructions for the NervaPy ARM assembler library.

## Changes Made

### 1. New Instruction Class (`nervapy/arm/generic.py`)
- Added `DualRegisterLoadStoreInstruction` class
- Handles both STRD and LDRD instructions
- Validates consecutive even/odd register pairs
- Supports all addressing modes including writeback

### 2. Instruction Functions (`nervapy/arm/generic.py`)
- Added `STRD(register_low, register_high, address, writeback=False)` function
- Added `LDRD(register_low, register_high, address, writeback=False)` function
- Both functions support comprehensive documentation and usage examples
- New `writeback` parameter for convenient pre-indexed writeback

### 3. Module Exports (`nervapy/arm/__init__.py`)
- Exported STRD and LDRD functions for public use

## Features Implemented

### Writeback Options (Enhanced)
- **No Writeback**: `STRD(r4, r5, [r12])` / `STRD(r4, r5, [r12, 8])`
- **Pre-indexed (Method 1)**: `STRD(r4, r5, [r12, 8], writeback=True)` *(NEW)*
- **Pre-indexed (Method 2)**: `STRD(r4, r5, [GeneralPurposeRegisterWriteback(r12), 8])`
- **Post-indexed**: `STRD(r4, r5, [r12], 8)`

The new `writeback=True` parameter provides a cleaner, more explicit way to enable pre-indexed writeback without needing to import or create GeneralPurposeRegisterWriteback objects.

### Register Validation
- Ensures both registers are general-purpose registers
- Validates consecutive even/odd register pairs (r0,r1 / r2,r3 / r4,r5 etc.)
- Proper error messages for invalid register combinations

### Memory Address Validation
- Supports 8-bit signed offset range (-255 to +255)
- Validates memory address format
- Handles writeback addressing modes correctly

## Usage Examples

```python
from nervapy.arm import *

# Basic store/load
STRD(r4, r5, [r12])           # Store r4,r5 to [r12]
LDRD(r0, r1, [r2])            # Load r0,r1 from [r2]

# With immediate offset
STRD(r4, r5, [r12, 8])        # Store to [r12+8]
LDRD(r0, r1, [r2, -16])       # Load from [r2-16]

# With writeback (NEW: using writeback parameter)
STRD(r4, r5, [r12, 8], writeback=True)   # Store to [r12+8], then r12 = r12+8
LDRD(r0, r1, [r2, -8], writeback=True)   # Load from [r2-8], then r2 = r2-8

# With writeback (traditional approach - still works)
from nervapy.arm.registers import GeneralPurposeRegisterWriteback
r12_wb = GeneralPurposeRegisterWriteback(r12)
STRD(r4, r5, [r12_wb, 8])     # Store to [r12+8], then r12 = r12+8

# Post-indexed writeback
STRD(r4, r5, [r12], 8)        # Store to [r12], then r12 = r12+8
LDRD(r0, r1, [r2], -8)        # Load from [r2], then r2 = r2-8
```

## Architecture Support
- Available from ARMv5E architecture onwards
- Tested with Cortex-A9 microarchitecture
- Compatible with existing ARM instruction set

## Integration
- Seamlessly integrated with existing NervaPy ARM infrastructure
- Uses same operand validation system as other load/store instructions
- Maintains compatibility with all existing ARM instructions
- Follows established coding patterns and conventions

## Testing
- Comprehensive test coverage for all addressing modes
- Validation of register constraints
- Integration testing with existing instruction set
- Error case handling verification

The STRD/LDRD instructions are now fully functional and ready for use in ARM assembly generation with NervaPy.