# ARMCC External Function Import Support

## Summary

Added support for declaring external functions in ARM assembly for ARMCC compiler using `IMPORT` directives.

## Problem

When using ARMCC (ARM Compiler), calling external functions requires IMPORT declarations. For example:

```assembly
    AREA    ||.text||, CODE, READONLY
    IMPORT  printf        ; Declare external function
    
my_function    PROC
    EXPORT  my_function
    BL      printf        ; Call external function
    BX      lr
    ENDP
    END
```

## Solution

Added `IMPORT.FUNCTION()` to declare external functions that automatically generates IMPORT directives in ARMCC format.

### Usage

```python
from nervapy.arm import Function, IMPORT, BL, BX, MOV, r0, lr
from nervapy.arm.abi import arm_gnueabi
from nervapy.arm.formats import AssemblyFormat
from nervapy.arm.microarchitecture import Microarchitecture

with Function("my_function", (), None,
              target=Microarchitecture.CortexM4,
              abi=arm_gnueabi,
              assembly_format=AssemblyFormat.ARMCC) as func:
    
    # Declare external function
    printf_func = IMPORT.FUNCTION("printf")
    
    # Use it
    MOV(r0, 0x100)
    BL(printf_func)
    BX(lr)
```

### Generated ARMCC Assembly

```assembly
        AREA    ||.text||, CODE, READONLY
        REQUIRE VFPv4

        IMPORT  printf

my_function    PROC
        EXPORT  my_function
my_function_ENTRY
        MOV r0, #256
        BL printf
        BX lr
        ENDP
        END
```

## Implementation Details

### Changes Made

1. **Added `ExternalFunction` class** (`nervapy/arm/pseudo.py`)
   - Represents an external function reference
   - Stores the function name

2. **Added `IMPORT.FUNCTION()` method** (`nervapy/arm/pseudo.py`)
   - Declares an external function
   - Registers it with the active function
   - Returns an `ExternalFunction` object for use with `BL`

3. **Updated `Function` class** (`nervapy/arm/function.py`)
   - Added `external_functions` set to track imported functions
   - Modified `_generate_armcc_assembly()` to output IMPORT directives

4. **Updated `Operand` class** (`nervapy/arm/instructions.py`)
   - Added support for `ExternalFunction` as a label type
   - Allows `BL` to accept `ExternalFunction` objects

5. **Updated `BranchWithLinkInstruction`** (`nervapy/arm/generic.py`)
   - Tracks if the target is an external function
   - Formats external functions without 'L' prefix

6. **Updated exports** (`nervapy/arm/__init__.py`)
   - Exported `IMPORT` class
   - Exported `ExternalFunction` class

### How It Works

1. **Declaration**: `IMPORT.FUNCTION("name")` creates an `ExternalFunction` object and registers it
2. **Tracking**: The function name is added to `Function.external_functions` set
3. **Code Generation**: During ARMCC assembly generation, all external functions are output as IMPORT directives
4. **Usage**: `BL(external_func)` uses the function name directly without the 'L' prefix

## Examples

### Simple External Call

```python
with Function("test", (), None,
              target=Microarchitecture.CortexM4,
              abi=arm_gnueabi,
              assembly_format=AssemblyFormat.ARMCC) as func:
    
    ext_func = IMPORT.FUNCTION("external_function")
    BL(ext_func)
    BX(lr)
```

Output:
```assembly
    IMPORT  external_function

test    PROC
    EXPORT  test
    BL external_function
    BX lr
    ENDP
    END
```

### Multiple External Functions

```python
malloc_func = IMPORT.FUNCTION("malloc")
memcpy_func = IMPORT.FUNCTION("memcpy")
free_func = IMPORT.FUNCTION("free")

BL(malloc_func)
# ... use malloc result ...
BL(memcpy_func)
# ... 
BL(free_func)
```

Output:
```assembly
    IMPORT  free
    IMPORT  malloc
    IMPORT  memcpy
```

(Functions are sorted alphabetically)

### Conditional External Call

```python
error_handler = IMPORT.FUNCTION("handle_error")

CMP(r0, 0)
skip_label = Label("skip")
BEQ(skip_label)
BL(error_handler)
LABEL(skip_label)
```

Output:
```assembly
    IMPORT  handle_error

    CMP r0, #0
    BEQ test_skip
    BL handle_error
test_skip
```

## Common External Functions

### C Standard Library
- `printf`, `sprintf`, `snprintf` - Formatted output
- `malloc`, `calloc`, `free` - Memory allocation
- `memcpy`, `memset`, `memmove` - Memory operations
- `strlen`, `strcmp`, `strcpy` - String operations
- `sin`, `cos`, `sqrt`, `pow` - Math functions

### Custom Libraries
```python
# Custom application functions
my_init = IMPORT.FUNCTION("app_initialize")
my_process = IMPORT.FUNCTION("process_data")
my_cleanup = IMPORT.FUNCTION("cleanup")

BL(my_init)
BL(my_process)
BL(my_cleanup)
```

## Assembly Format Support

### ARMCC Format (IMPORT Directives Generated)
When using `AssemblyFormat.ARMCC`:
- Generates `IMPORT function_name` directives
- Functions sorted alphabetically
- Placed after AREA declaration, before PROC
- **Required for external function calls in ARMCC**

Example:
```assembly
    AREA    ||.text||, CODE, READONLY
    IMPORT  printf        ← Only in ARMCC format
    
my_function    PROC
    BL printf
    ENDP
```

### GAS Format (No IMPORT Needed)
When using `AssemblyFormat.GAS`:
- **No IMPORT directives generated** (not needed by GAS)
- External functions referenced directly
- Linker resolves symbols automatically

Example:
```assembly
    .text
.global my_function
my_function:
    BL printf        ← No IMPORT declaration needed
    BX lr
```

### Format Detection

The IMPORT directive generation is **automatic and format-aware**:
- `IMPORT.FUNCTION()` registers the external function
- When generating ARMCC assembly → IMPORT directives added
- When generating GAS assembly → No IMPORT directives (GAS doesn't need them)

## Testing

All tests pass successfully:

```
✓ Simple external function call
✓ Multiple external functions (sorted)
✓ Conditional external calls
✓ GAS vs ARMCC format comparison
✓ IMPORT directives generated correctly
✓ External functions called without 'L' prefix
```

## Files Modified/Created

**Modified:**
1. `nervapy/arm/pseudo.py` - Added `ExternalFunction` and `IMPORT` classes
2. `nervapy/arm/function.py` - Added external function tracking and IMPORT generation
3. `nervapy/arm/instructions.py` - Added `ExternalFunction` support in `Operand`
4. `nervapy/arm/generic.py` - Updated `BranchWithLinkInstruction` for external functions
5. `nervapy/arm/__init__.py` - Exported `IMPORT` and `ExternalFunction`

**Created:**
6. `examples/arm_import_external_functions.py` - Comprehensive examples
7. `docs/ARM_IMPORT_EXTERNAL_FUNCTIONS.md` - This documentation

## Benefits

1. **Correct ARMCC syntax** - Automatically generates proper IMPORT directives
2. **Type safety** - ExternalFunction objects prevent typos
3. **Automatic tracking** - No manual management of imports needed
4. **Format-independent** - Works with both GAS and ARMCC formats
5. **Clean API** - Simple, intuitive interface

## Example Output Comparison

**Before** (manual):
```python
# User had to manually add IMPORT somehow
BL("printf")  # No IMPORT generated!
```

**After** (automatic):
```python
printf_func = IMPORT.FUNCTION("printf")
BL(printf_func)  # IMPORT directive automatically generated!
```

## Summary

✅ **IMPORT support successfully added to NervaPy for ARMCC external function calls!**

The implementation:
- Provides clean API for declaring external functions
- Automatically generates IMPORT directives for ARMCC
- Maintains compatibility with GAS format
- Tracks and deduplicates external function references
- Works seamlessly with existing BL instruction
