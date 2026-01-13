# ARMv7-M Branch Instructions Added to NervaPy

## Summary of Changes

All requested ARMv7-M branch instructions have been successfully added to NervaPy:

**B** - Unconditional branch (was already present, now exported)  
**BLO** - Branch if Lower (was already present)  
**BX** - Branch and Exchange (was present but restricted, now fixed to accept any register)  
**BL** - Branch with Link (was already present)  
**BLX** - Branch with Link and Exchange (**NEW - added**)

## Changes Made

### 1. Added BLX Instruction

Created a new `BranchLinkExchangeInstruction` class and `BLX()` function for indirect function calls with link.

**Location:** `nervapy/arm/generic.py`

```python
class BranchLinkExchangeInstruction(Instruction):
    """Branch with Link and Exchange - indirect function call"""
    def __init__(self, destination, origin=None):
        from nervapy.arm.registers import lr
        super(BranchLinkExchangeInstruction, self).__init__('BLX', [destination], origin=origin)
        self.lr = lr
        if destination.is_general_purpose_register():
            pass
        else:
            raise ValueError('Invalid operands in instruction {0} {1}'.format('BLX', destination))

def BLX(destination):
    """Branch with Link and Exchange to register"""
    origin = inspect.stack() if nervapy.arm.function.active_function.collect_origin else None
    instruction = BranchLinkExchangeInstruction(Operand(destination), origin=origin)
    if nervapy.stream.active_stream is not None:
        nervapy.stream.active_stream.add_instruction(instruction)
    return instruction
```

### 2. Fixed BX Instruction

The `BX` instruction was too restrictive - it only accepted `lr` as a destination. Fixed to accept any general-purpose register.

**Before:**
```python
if destination.is_general_purpose_register() and destination.register == lr:
    pass  # Only accepted lr
```

**After:**
```python
if destination.is_general_purpose_register():
    pass  # Accepts any register
```

### 3. Updated Exports

Updated `nervapy/arm/__init__.py` to export the new and previously missing instructions:
- Added `B` to exports
- Added `BLX` to exports  
- Added `BX` to exports

## Usage Examples

### Basic Usage

```python
from nervapy.arm.registers import r0, r1, r2, r3, lr
from nervapy.arm.generic import B, BLO, BX, BL, BLX
from nervapy.arm.pseudo import Label

# B - Unconditional branch
loop = Label("main_loop")
B(loop)

# BLO - Branch if Lower (after a compare)
error_handler = Label("error")
BLO(error_handler)

# BX - Branch and Exchange (typically for returns)
BX(lr)  # Return from function

# BL - Branch with Link (function call)
func = Label("my_function")
BL(func)

# BLX - Branch with Link and Exchange (indirect function call)
BLX(r3)  # Call function pointer in r3
```

### Complete Example: Function with Callback

```python
from nervapy.arm.registers import r0, lr
from nervapy.arm.generic import BLX, BX

# Call a callback function
# r0 contains the function pointer
BLX(r0)  # Call the callback

# Return from function
BX(lr)   # Return to caller
```

## Instruction Reference

### Unconditional Branches

| Instruction | Syntax | Description | Use Case |
|-------------|--------|-------------|----------|
| `B` | `B(label)` | Branch to label | Loops, unconditional jumps |
| `BX` | `BX(register)` | Branch to address in register | Function returns (`BX(lr)`) |
| `BL` | `BL(label)` | Branch with Link to label | Direct function calls |
| `BLX` | `BLX(register)` | Branch with Link to register | Indirect function calls |

### Conditional Branches

All conditional branches are also available (after comparison instructions):

- `BEQ` - Branch if Equal
- `BNE` - Branch if Not Equal
- `BLO` - Branch if Lower (unsigned)
- `BHS` - Branch if Higher or Same (unsigned)
- `BLT` - Branch if Less Than (signed)
- `BGE` - Branch if Greater or Equal (signed)
- `BGT` - Branch if Greater Than (signed)
- `BLE` - Branch if Less or Equal (signed)
- And more...

## Key Differences

### BX vs BL vs BLX

| Instruction | Target | Saves Return Address | Use Case |
|-------------|--------|---------------------|----------|
| `BX` | Register | No | Returns, indirect jumps |
| `BL` | Label | Yes (in LR) | Direct function calls |
| `BLX` | Register | Yes (in LR) | Indirect function calls |

### Common Patterns

**Function Return:**
```python
BX(lr)  # Return to caller
```

**Direct Function Call:**
```python
BL(Label("function_name"))  # Call function
```

**Indirect Function Call (Function Pointer):**
```python
BLX(r3)  # Call function at address in r3
```

## Testing

All instructions have been tested and verified to work correctly:

```
✓ B     - Unconditional branch to label
✓ BLO   - Branch if Lower (conditional)
✓ BX    - Branch and exchange to any register
✓ BL    - Branch with link to label
✓ BLX   - Branch with link and exchange to any register
```

## Files Modified

1. **`nervapy/arm/generic.py`**
   - Fixed `BranchExchangeInstruction` class to accept any register
   - Added `BranchLinkExchangeInstruction` class
   - Added `BLX()` function

2. **`nervapy/arm/__init__.py`**
   - Added `B`, `BLX`, and `BX` to exports

3. **`examples/arm_branch_instructions.py`** (new file)
   - Comprehensive examples of all branch instructions
   - Real-world usage patterns
   - Complete instruction reference

4. **`docs/ARM_BRANCH_INSTRUCTIONS.md`** (this file)
   - Complete documentation

## Additional Resources

- **Example Script:** `examples/arm_branch_instructions.py`
- **ARM Architecture Reference:** ARMv7-M Architecture Reference Manual, Section A7.7 (Branch instructions)

## Notes

- All branch instructions follow ARMv7-M architecture specifications
- `BX` and `BLX` can use any general-purpose register (r0-r15)
- `BL` always saves the return address in the Link Register (LR/r14)
- `BLX` is commonly used for function pointers and virtual function calls
- All conditional branches require a preceding comparison or test instruction
