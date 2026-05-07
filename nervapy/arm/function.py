# This file is part of PeachPy package and is licensed under the Simplified BSD license.
#    See license.rst for the full text of the license.

from __future__ import print_function

import time

import nervapy.arm.instructions
import nervapy.arm.registers
from nervapy.arm.microarchitecture import Microarchitecture

active_function = None


class Function(object):
    def __init__(
        self,
        name,
        arguments,
        return_type=None,
        target=Microarchitecture.Default,
        abi=None,
        assembly_format=None,
        high_register_strategy=None,
        collect_origin=False,
        dump_intermediate_assembly=False,
        report_generation=True,
        report_live_registers=False,
        is_thumb=False,
        alignment=0,
        validate_stack_alignment=True,
        preserve8=False,
    ):
        self.name = name
        self.arguments = arguments
        self.return_type = return_type
        self.is_thumb = is_thumb
        self.alignment = alignment
        self.validate_stack_alignment = validate_stack_alignment
        self.preserve8 = preserve8

        # Set default assembly format to GAS if not specified
        if assembly_format is None:
            from nervapy.arm.formats import AssemblyFormat

            assembly_format = AssemblyFormat.GAS
        self.assembly_format = assembly_format

        # Set default high register strategy if not specified
        if high_register_strategy is None:
            from nervapy.arm.formats import HighRegisterStrategy

            high_register_strategy = HighRegisterStrategy.AUTO
        self.high_register_strategy = high_register_strategy

        for argument in self.arguments:
            argument.stack_offset = None
            argument.register = None
            if (
                argument.is_size_integer
                or argument.is_pointer_integer
                or argument.is_pointer
            ):
                argument.c_type.size = abi.pointer_size
            assert argument.size
        self.target = target
        self.abi = abi
        self.collect_origin = collect_origin
        self.dump_intermediate_assembly = dump_intermediate_assembly
        self.report_generation = report_generation
        self.report_live_registers = report_live_registers
        self.ticks = None

        # Assign argument locations
        from nervapy.arm.abi import arm_gnueabi, arm_gnueabihf
        from nervapy.arm.registers import r0, r1, r2, r3

        if abi == arm_gnueabi or abi == arm_gnueabihf:
            # Up to 4 first arguments are passed in registers, others passed through stack
            # Arguments smaller than 4 bytes are extended to 4 bytes (both when passed on stack or in a register).
            # 8-byte arguments occupy 2 general-purpose registers or 8 bytes on stack. When they are passed in
            # registers, the index of the first register must be even (i.e. they are passed in (r0, r1) or (r2, r3),
            # but not in (r1, r2). When 8-byte arguments are passed on stack, their location is aligned on 8 bytes,
            # skipping 4 bytes if necessary.
            argument_registers = (r0, r1, r2, r3)
            register_offset = 0
            stack_offset = 0
            for argument in self.arguments:
                if argument.size <= 4:
                    if register_offset < 4:
                        argument.register = argument_registers[register_offset]
                        register_offset += 1
                    else:
                        argument.stack_offset = stack_offset
                        stack_offset += 4
                elif argument.size == 8:
                    # First register index must be even
                    if register_offset % 2 == 1:
                        register_offset += 1
                    if register_offset < 4:
                        argument.register = (
                            argument_registers[register_offset],
                            argument_registers[register_offset + 1],
                        )
                        register_offset += 2
                    else:
                        if stack_offset % 8 == 4:
                            stack_offset += 4
                        argument.stack_offset = stack_offset
                        stack_offset += 8
                else:
                    raise ValueError(
                        "Unsupported argument size {0}".format(argument.size)
                    )
        else:
            raise ValueError("Unsupported assembler ABI %s" % abi)

        self.instructions = list()
        self.constants = list()
        self.external_functions = set()  # Track external function imports
        self.stack_frame = StackFrame(self.abi)
        self.local_variables_count = 0
        self.virtual_registers_count = 0x40
        self.conflicting_registers = dict()
        self.allocation_options = dict()
        self.unallocated_registers = list()
        self._live_register_markers = []  # List of (instruction_index, label) tuples
        self._register_names = {}  # Map from register number to variable name

    def __enter__(self):
        import nervapy.stream

        global active_function

        if active_function is not None:
            raise ValueError(
                "Function {0} was not detached".format(active_function.name)
            )
        if nervapy.stream.active_stream is not None:
            raise ValueError("Alternative instruction stream is active")
        active_function = self
        nervapy.stream.active_stream = self
        if self.report_generation:
            print(
                "Generating function {Function} for microarchitecture {Microarchitecture} and ABI {ABI}".format(
                    Function=self.name, Microarchitecture=self.target, ABI=self.abi
                )
            )
            print("\tParsing source", end="")
            self.ticks = time.time()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        import nervapy.stream
        from nervapy.arm.instructions import Instruction

        nervapy.stream.active_stream = None
        if exc_type is None:
            try:
                self.generate_labels()
                self.decompose_instructions()
                self.reserve_registers()
                if self.report_generation:
                    elapsed = time.time() - self.ticks
                    print(" (%2.2f secs)" % elapsed)
                    print("\tRunning liveness analysis", end="")
                    self.ticks = time.time()
                self.determine_available_registers()
                self.determine_live_registers(exclude_parameter_loads=True)
                
                # Report live registers at marked points
                if self._live_register_markers:
                    self._report_live_registers_at_markers()

                if self.dump_intermediate_assembly:
                    with open(
                        "%s.S" % self.symbol_name, "w"
                    ) as intermediate_assembly_file:
                        for instruction in self.instructions:
                            if isinstance(instruction, Instruction):
                                consumed_registers = ", ".join(
                                    sorted(
                                        map(
                                            str,
                                            list(
                                                instruction.get_input_registers_list()
                                            ),
                                        )
                                    )
                                )
                                produced_registers = ", ".join(
                                    sorted(
                                        map(
                                            str,
                                            list(
                                                instruction.get_output_registers_list()
                                            ),
                                        )
                                    )
                                )
                                available_registers = ", ".join(
                                    sorted(
                                        map(str, list(instruction.available_registers))
                                    )
                                )
                                live_registers = ", ".join(
                                    sorted(map(str, list(instruction.live_registers)))
                                )
                                intermediate_assembly_file.write(
                                    str(instruction) + "\n"
                                )
                                intermediate_assembly_file.write(
                                    "\tConsumed registers: " + consumed_registers + "\n"
                                )
                                intermediate_assembly_file.write(
                                    "\tProduced registers: " + produced_registers + "\n"
                                )
                                intermediate_assembly_file.write(
                                    "\tLive registers: " + live_registers + "\n"
                                )
                                if instruction.line_number:
                                    intermediate_assembly_file.write(
                                        "\tLine: " + str(instruction.line_number) + "\n"
                                    )
                                if instruction.source_code:
                                    intermediate_assembly_file.write(
                                        "\tCode: " + instruction.source_code + "\n"
                                    )
                            else:
                                intermediate_assembly_file.write(
                                    str(instruction) + "\n"
                                )

                if self.report_generation:
                    elapsed = time.time() - self.ticks
                    print(" (%2.2f secs)" % elapsed)
                    print("\tRunning register allocation", end="")
                    self.ticks = time.time()
                self.check_live_registers()
                self.determine_register_relations()
                self.allocate_registers()

                if self.report_generation:
                    elapsed = time.time() - self.ticks
                    print(" (%2.2f secs)" % elapsed)
                    print("\tGenerating code", end="")
                    self.ticks = time.time()
                self.remove_assume_statements()
                self.update_stack_frame()
                self.generate_parameter_loads()
                if self.report_live_registers:
                    self.determine_live_registers()
                self.generate_prolog_and_epilog()
                if self.validate_stack_alignment:
                    self.validate_stack_alignment_check()

                self.generate_constant_loads()
                self.optimize_instructions()
                if self.report_generation:
                    elapsed = time.time() - self.ticks
                    print(" (%2.2f secs)" % elapsed)
                    self.ticks = time.time()
            finally:
                self.detach()
        else:
            self.detach()

    def find_argument(self, argument_target):
        from nervapy import Argument

        assert isinstance(
            argument_target, (Argument, str)
        ), "Either Argument object or argument name expected"
        if isinstance(argument_target, Argument):
            if argument_target in self.arguments:
                return argument_target
            else:
                return None
        else:
            return next(
                (
                    argument
                    for argument in self.arguments
                    if argument.name == argument_target
                ),
                None,
            )

    def detach(self):
        import nervapy.stream

        global active_function
        if active_function is None:
            raise ValueError("Trying to detach a function while no function is active")
        active_function = None
        nervapy.stream.active_stream = None
        return self

    @property
    def assembly(self):
        """Generate assembly code in the specified format."""
        from nervapy.arm.formats import AssemblyFormat

        if self.assembly_format == AssemblyFormat.ARMCC:
            return self._generate_armcc_assembly()
        else:  # Default to GAS format
            return self._generate_gas_assembly()

    def _generate_constant_data_section(self):
        """Generate .data section for ConstantData objects"""
        try:
            from nervapy.constant_data import ConstantData
            constants = ConstantData.get_function_constants(self)
            if not constants:
                return ""

            import os
            lines = []
            lines.append("")
            lines.append("\t.data")
            lines.append("\t.align 4")
            for const in constants:
                lines.append(const.generate_data_section())
            return os.linesep.join(lines)
        except ImportError:
            return ""


    @property
    def global_asm(self):
        """Generate a Rust global_asm!() macro call embedding the GAS assembly.

        Usage in a Rust source file:
            use core::arch::global_asm;
            include!("generated_kernels.rs");  // or paste directly

        The extern declaration goes in your Rust code:
            unsafe extern "C" { fn my_func(a: u32) -> u32; }
        """
        gas = self._generate_gas_assembly()
        return 'core::arch::global_asm!(r#"\n{asm}"#);\n'.format(
            asm=self._escape_rust_asm_template(gas)
        )

    @staticmethod
    def _escape_rust_asm_template(asm):
        return asm.replace("{", "{{").replace("}", "}}")

    def _rust_ffi_type(self, c_type):
        if c_type.is_pointer:
            pointee = c_type.base
            if pointee is None:
                pointee_type = "core::ffi::c_void"
                is_const_pointee = c_type.is_const
            else:
                pointee_type = self._rust_ffi_type(pointee)
                is_const_pointee = pointee.is_const
            return "{0} {1}".format(
                "*const" if is_const_pointee else "*mut", pointee_type
            )

        if c_type.is_size_integer:
            return "usize" if c_type.is_unsigned_integer else "isize"
        if c_type.is_pointer_integer:
            return "usize" if c_type.is_unsigned_integer else "isize"
        if c_type.is_bool:
            return "bool"
        if c_type.is_char:
            return "core::ffi::c_char"
        if c_type.is_wchar:
            wchar_size = c_type.get_size(self.abi)
            return {2: "u16", 4: "u32"}[wchar_size]
        if c_type.is_floating_point:
            return {2: "u16", 4: "f32", 8: "f64"}[c_type.get_size(self.abi)]
        if c_type.is_signed_integer:
            return {1: "i8", 2: "i16", 4: "i32", 8: "i64"}[c_type.get_size(self.abi)]
        if c_type.is_unsigned_integer:
            return {1: "u8", 2: "u16", 4: "u32", 8: "u64"}[c_type.get_size(self.abi)]

        raise ValueError("Unsupported Rust FFI type for {0}".format(c_type))

    @property
    def rust_extern_declaration(self):
        args = ", ".join(
            "{0}: {1}".format(argument.name, self._rust_ffi_type(argument.c_type))
            for argument in self.arguments
        )
        signature = "pub fn {0}({1})".format(self.name, args)
        if self.return_type is not None:
            signature += " -> {0}".format(self._rust_ffi_type(self.return_type))
        return signature + ";"

    @property
    def rust_extern(self):
        return "unsafe extern \"C\" {{\n    {0}\n}}\n".format(
            self.rust_extern_declaration
        )

    @property
    def rust_module(self):
        return self.global_asm + "\n" + self.rust_extern

    def _generate_gas_assembly(self):
        """Generate assembly code in GNU Assembler (GAS) format."""
        import os

        from nervapy.arm.generic import BranchInstruction
        from nervapy.arm.instructions import Instruction
        from nervapy.arm.pseudo import LabelQuasiInstruction

        function_label = self.name
        constants_label = self.name + "_constants"
        assembly = ""
        assembly += "\t.syntax unified" + os.linesep
        if self.is_thumb:
            assembly += "\t.thumb" + os.linesep
        assembly += "\t" + self.gnu_arch_spec + os.linesep

        # Generate .data section for ConstantData if present
        constant_data_section = self._generate_constant_data_section()
        if constant_data_section:
            assembly += constant_data_section + os.linesep

        if len(self.constants) > 0:
            assembly += (
                "section .rodata.{Microarchitecture} progbits alloc noexec nowrite align={Alignment}".format(
                    Microarchitecture=self.target.id, Alignment=32
                )
                + os.linesep
            )
            assembly += constants_label + ":" + os.linesep
            data_declaration_map = {8: "DB", 16: "DW", 32: "DD", 64: "DQ", 128: "DO"}
            need_alignment = False
            for constant_bucket in self.constants:
                if need_alignment:
                    assembly += (
                        "\tALIGN {Alignment}".format(Alignment=constant_bucket.capacity)
                        + os.linesep
                    )
                for constant in constant_bucket.constants:
                    assembly += (
                        "\t.{Label}: {Declaration} {Value}".format(
                            Label=constant.label,
                            Declaration=data_declaration_map[constant.size],
                            Value=", ".join([str(constant)] * constant.repeats),
                        )
                        + os.linesep
                    )
                need_alignment = not constant_bucket.is_full()
            assembly += os.linesep

        if hasattr(self, "external_functions") and len(self.external_functions) > 0:
            for func_name in sorted(self.external_functions):
                assembly += ".extern {0}".format(func_name) + os.linesep
            assembly += os.linesep

        assembly += "\n\t.text\n" + os.linesep
        assembly += ".global {Function}".format(Function=function_label) + os.linesep
        assembly += (
            ".type {Function}, %function".format(Function=function_label) + os.linesep
        )
        if self.alignment > 0:
            assembly += (
                ".align {Alignment}".format(Alignment=self.alignment) + os.linesep
            )
        assembly += function_label + ":" + os.linesep
        if self.gnu_fpu_spec:
            assembly += "\t" + self.gnu_fpu_spec + os.linesep
        for instruction in self.instructions:
            if isinstance(instruction, BranchInstruction):
                assembly += (
                    "\t"
                    + "{0} L{1}.{2}".format(
                        instruction.name, self.name, instruction.operands[0].label
                    )
                    + os.linesep
                )
            elif isinstance(instruction, Instruction):
                constant = instruction.get_constant()
                if constant is not None:
                    constant.prefix = constants_label
                assembly += "\t" + str(instruction) + os.linesep
            elif isinstance(instruction, LabelQuasiInstruction):
                assembly += "L{0}.{1}:".format(self.name, instruction.name) + os.linesep
            else:
                assembly += "\t" + str(instruction) + os.linesep

        # Generate literal pool if present
        if hasattr(self, 'literal_pool') and self.literal_pool.entries:
            assembly += os.linesep
            assembly += self.literal_pool.generate_assembly(format='gas') + os.linesep

        assembly += os.linesep
        return assembly

    def _generate_armcc_assembly(self):
        """Generate assembly code in ARM Compiler (ARMCC) format."""
        import os

        from nervapy.arm.generic import BranchInstruction
        from nervapy.arm.instructions import Instruction
        from nervapy.arm.pseudo import LabelQuasiInstruction

        function_label = self.name
        constants_label = self.name + "_constants"
        assembly = ""

        if self.is_thumb:
            assembly += "        THUMB" + os.linesep

        # ARMCC constants section
        if len(self.constants) > 0:
            assembly += "        AREA    ||.constdata||, DATA, READONLY" + os.linesep
            assembly += constants_label + os.linesep
            data_declaration_map = {
                8: "DCB",
                16: "DCW",
                32: "DCD",
                64: "DCDU",
                128: "DCDU",
            }
            for constant_bucket in self.constants:
                for constant in constant_bucket.constants:
                    assembly += (
                        "{Label}    {Declaration}    {Value}".format(
                            Label=constant.label,
                            Declaration=data_declaration_map[constant.size],
                            Value=", ".join([str(constant)] * constant.repeats),
                        )
                        + os.linesep
                    )
            assembly += os.linesep

        # ARMCC code section
        assembly += "        AREA    ||.text||, CODE, READONLY"
        if self.alignment > 0:
            assembly += ", ALIGN={0}".format(self.alignment)
        assembly += os.linesep
        if self.preserve8:
            assembly += "        PRESERVE8" + os.linesep
        if self.armcc_fpu_spec:
            assembly += "        " + self.armcc_fpu_spec + os.linesep
        assembly += os.linesep

        # Add IMPORT statements for external functions
        if hasattr(self, "external_functions") and len(self.external_functions) > 0:
            for func_name in sorted(self.external_functions):
                assembly += "        IMPORT  " + func_name + os.linesep
            assembly += os.linesep

        assembly += function_label + "    PROC" + os.linesep
        assembly += "        EXPORT  " + function_label + os.linesep

        for instruction in self.instructions:
            if isinstance(instruction, BranchInstruction):
                assembly += (
                    "        "
                    + "{0} {1}_{2}".format(
                        instruction.name, self.name, instruction.operands[0].label
                    )
                    + os.linesep
                )
            elif isinstance(instruction, Instruction):
                constant = instruction.get_constant()
                if constant is not None:
                    constant.prefix = constants_label
                assembly += "        " + str(instruction) + os.linesep
            elif isinstance(instruction, LabelQuasiInstruction):
                assembly += "{0}_{1}".format(self.name, instruction.name) + os.linesep
            else:
                assembly += "        " + str(instruction) + os.linesep

        # Generate literal pool if present
        if hasattr(self, 'literal_pool') and self.literal_pool.entries:
            assembly += os.linesep
            assembly += self.literal_pool.generate_assembly(format='armcc') + os.linesep

        assembly += "        ENDP" + os.linesep
        assembly += "        END" + os.linesep
        return assembly

    @property
    def gnu_arch_spec(self):
        from nervapy.arm.isa import Extension

        isa_extensions = self.isa_extensions
        if Extension.V8_1MMain in isa_extensions:
            return ".arch armv8.1-m.main"
        elif Extension.V8MMain in isa_extensions:
            return ".arch armv8-m.main"
        elif Extension.Div in isa_extensions:
            return ".cpu cortex-a15"
        elif Extension.V7MP in isa_extensions:
            return ".cpu cortex-a9"
        elif Extension.V7M in isa_extensions:
            return ".arch armv7-m"
        elif Extension.V8MBase in isa_extensions:
            return ".arch armv8-m.base"
        elif Extension.V7 in isa_extensions:
            return ".arch armv7-a"
        elif Extension.V6K in isa_extensions:
            return ".arch armv6zk"
        elif Extension.V6 in isa_extensions:
            return ".arch armv6"
        elif Extension.V5E in isa_extensions:
            return ".arch armv5te"
        else:
            return ".arch armv5t"

    @property
    def gnu_fpu_spec(self):
        from nervapy.arm.isa import Extension

        isa_extensions = self.isa_extensions
        # ARMv8-M (Cortex-M33, M35P, etc.) uses FPv5-SP
        if Extension.V8MMain in isa_extensions or Extension.V8MBase in isa_extensions:
            if Extension.MVE in isa_extensions:
                return ".fpu mve"
            elif Extension.VFP4 in isa_extensions or Extension.VFP3 in isa_extensions:
                # ARMv8-M has FPv5 single-precision FPU
                return ".fpu fpv5-sp-d16"
            else:
                return None
        # ARMv8.1-M (Cortex-M55, etc.) with Helium MVE
        elif Extension.V8_1MMain in isa_extensions:
            if Extension.MVE in isa_extensions:
                return ".fpu mve"
            elif Extension.VFP4 in isa_extensions or Extension.VFP3 in isa_extensions:
                return ".fpu fpv5-sp-d16"
            else:
                return None
        elif Extension.NEON2 in isa_extensions or (Extension.VFP4 in isa_extensions and Extension.NEON in isa_extensions):
            return ".fpu neon-vfpv4"
        elif (
            Extension.NEONHP in isa_extensions
            or Extension.VFPHP in isa_extensions
            and Extension.NEON in isa_extensions
        ):
            return ".fpu neon-fp16"
        elif Extension.NEON in isa_extensions:
            return ".fpu neon"
        elif Extension.VFPHP in isa_extensions:
            if Extension.VFPd32 in isa_extensions:
                return ".fpu vfpv3-fp16"
            else:
                return ".fpu vfpv3-d16-fp16"
        elif Extension.VFP3 in isa_extensions:
            if Extension.VFPd32 in isa_extensions:
                return ".fpu vfpv3"
            else:
                return ".fpu vfpv3-d16"
        elif Extension.VFP in isa_extensions or Extension.VFP2 in isa_extensions:
            return
        elif Extension.VFP3 in isa_extensions:
            return ".fpu vfp"
        else:
            return None

    @property
    def armcc_arch_spec(self):
        """Generate ARMCC-compatible architecture specification."""
        from nervapy.arm.isa import Extension

        isa_extensions = self.isa_extensions
        if Extension.V7M in isa_extensions:
            return "ARM"
        elif Extension.V7MP in isa_extensions:
            return "ARM"
        elif Extension.V7 in isa_extensions:
            return "ARM"
        elif Extension.V6K in isa_extensions:
            return "ARM"
        elif Extension.V6 in isa_extensions:
            return "ARM"
        elif Extension.V5E in isa_extensions:
            return "ARM"
        else:
            return "ARM"

    @property
    def armcc_fpu_spec(self):
        """Generate ARMCC-compatible FPU specification."""
        from nervapy.arm.isa import Extension

        isa_extensions = self.isa_extensions
        if Extension.NEON2 in isa_extensions or Extension.VFP4 in isa_extensions:
            return "REQUIRE VFPv4"
        elif (
            Extension.NEONHP in isa_extensions
            or Extension.VFPHP in isa_extensions
            and Extension.NEON in isa_extensions
        ):
            return "REQUIRE VFPv3_FP16"
        elif Extension.NEON in isa_extensions:
            return "REQUIRE VFPv3"
        elif Extension.VFPHP in isa_extensions:
            return "REQUIRE VFPv3_FP16"
        elif Extension.VFP3 in isa_extensions:
            return "REQUIRE VFPv3"
        elif Extension.VFP in isa_extensions or Extension.VFP2 in isa_extensions:
            return "REQUIRE VFPv2"
        else:
            return None

    def add_instruction(self, instruction):
        from nervapy.arm.instructions import Instruction

        if instruction is None:
            return
        if isinstance(instruction, Instruction):
            for extension in instruction.isa_extensions:
                if extension not in self.target.extensions:
                    raise ValueError(
                        "{0} is not supported on the target microarchitecture".format(
                            extension
                        )
                    )
            local_variable = instruction.get_local_variable()
            if local_variable is not None:
                self.stack_frame.add_variable(local_variable.get_root())
            self.stack_frame.preserve_registers(instruction.get_output_registers_list())
        self.instructions.append(instruction)

    def add_instructions(self, instructions):
        for instruction in instructions:
            self.add_instruction(instruction)

    def preserve(self, *registers):
        """Force additional registers into the function prologue/epilogue.

        Use this when you need registers preserved that the automatic analysis
        would not detect (e.g. registers used only via inline logic or explicit
        control flow).  The registers are merged with the auto-detected ones so
        the prologue emits a single PUSH / PUSH.W covering everything.

        Accepts individual registers or a single tuple/list, mirroring the
        calling convention of PUSH::

            with Function("my_func", ...) as f:
                f.preserve(r8, r9)       # varargs style
                f.preserve((r8, r9))     # tuple style (like PUSH)
                f.preserve(lr)
        """
        for item in registers:
            if isinstance(item, (tuple, list)):
                for register in item:
                    self.stack_frame.force_preserve_register(register)
            else:
                self.stack_frame.force_preserve_register(item)

    def decompose_instructions(self):
        from nervapy.arm.pseudo import ReturnInstruction

        new_instructions = list()
        for instruction in self.instructions:
            if isinstance(instruction, ReturnInstruction):
                new_instructions.extend(instruction.to_instruction_list())
            else:
                new_instructions.append(instruction)
        self.instructions = new_instructions

    def generate_prolog_and_epilog(self):
        from nervapy.arm.generic import BranchExchangeInstruction
        from nervapy.arm.pseudo import LabelQuasiInstruction

        prologue_instructions = self.stack_frame.generate_prologue()
        epilogue_instructions = self.stack_frame.generate_epilogue()
        new_instructions = list()
        for instruction in self.instructions:
            if isinstance(instruction, LabelQuasiInstruction):
                new_instructions.append(instruction)
                if instruction.name == "ENTRY":
                    new_instructions.extend(prologue_instructions)
            elif isinstance(instruction, BranchExchangeInstruction):
                new_instructions.extend(epilogue_instructions)
                new_instructions.append(instruction)
            else:
                new_instructions.append(instruction)
        self.instructions = new_instructions

    def generate_labels(self):
        from nervapy.arm.instructions import Operand
        from nervapy.arm.pseudo import LabelQuasiInstruction

        for instruction in self.instructions:
            if isinstance(instruction, LabelQuasiInstruction):
                if instruction.name == "ENTRY":
                    break
        else:
            self.instructions.insert(0, LabelQuasiInstruction(Operand("ENTRY")))

    def get_label_table(self):
        from nervapy.arm.pseudo import LabelQuasiInstruction

        label_table = dict()
        for index, instruction in enumerate(self.instructions):
            if isinstance(instruction, LabelQuasiInstruction):
                label_table[instruction.name] = index
        return label_table

    def find_entry_label(self):
        from nervapy.arm.pseudo import LabelQuasiInstruction

        for index, instruction in enumerate(self.instructions):
            if isinstance(instruction, LabelQuasiInstruction):
                if instruction.name == "ENTRY":
                    return index
        raise ValueError("Instruction stream does not contain the ENTRY label")

    def find_exit_points(self):
        from nervapy.arm.generic import BranchExchangeInstruction

        ret_instructions = list()
        for index, instruction in enumerate(self.instructions):
            if isinstance(instruction, BranchExchangeInstruction):
                ret_instructions.append(index)
        return ret_instructions

    def determine_branches(self):
        from nervapy.arm.generic import BranchInstruction
        from nervapy.arm.pseudo import LabelQuasiInstruction

        label_table = self.get_label_table()
        for instruction in self.instructions:
            if isinstance(instruction, LabelQuasiInstruction):
                instruction.input_branches = set()

        for i, instruction in enumerate(self.instructions):
            if isinstance(instruction, BranchInstruction):
                target_label = instruction.operands[0].label
                target_index = label_table[target_label]
                self.instructions[target_index].input_branches.add(i)

    def reserve_registers(self):
        pass

    def determine_available_registers(self):
        from nervapy.arm.generic import BranchInstruction
        from nervapy.arm.instructions import Instruction

        processed_branches = set()
        label_table = self.get_label_table()

        def mark_available_registers(instructions, start, initial_available_registers):
            available_registers = set(initial_available_registers)
            for i in range(start, len(instructions)):
                instruction = instructions[i]
                if isinstance(instruction, Instruction):
                    instruction.available_registers = set(available_registers)
                    if isinstance(instruction, BranchInstruction):
                        if i not in processed_branches:
                            target_label = instruction.operands[0].label
                            target_index = label_table[target_label]
                            processed_branches.add(i)
                            mark_available_registers(
                                instructions, target_index, available_registers
                            )
                        if not instruction.is_conditional():
                            return
                    else:
                        available_registers |= set(
                            instruction.get_output_registers_list()
                        )

        current_index = self.find_entry_label()
        mark_available_registers(self.instructions, current_index, set())

    def determine_live_registers(self, exclude_parameter_loads=False):
        from nervapy.arm.generic import BranchInstruction
        from nervapy.arm.instructions import Instruction
        from nervapy.arm.pseudo import (LabelQuasiInstruction,
                                        LoadArgumentPseudoInstruction)
        from nervapy.arm.registers import Register

        self.determine_branches()
        for instruction in self.instructions:
            if isinstance(instruction, Instruction):
                live_registers = set()
            if isinstance(instruction, BranchInstruction):
                instruction.is_visited = False

        def mark_live_registers(instructions, exit_point, initial_live_registers):
            live_registers = dict(initial_live_registers)
            # Walk from the bottom to top of the linear block
            for i in range(exit_point, -1, -1):
                instruction = instructions[i]
                if (
                    isinstance(instruction, BranchInstruction)
                    and not instruction.is_conditional
                    and i != exit_point
                ):
                    return
                elif isinstance(instruction, Instruction):
                    # First mark registers which are written to by this instruction as non-live
                    # Then mark registers which are read by this instruction as live
                    for output_register in instruction.get_output_registers_list():
                        register_id = output_register.id
                        register_mask = output_register.mask
                        if register_id in live_registers:
                            live_registers[register_id] &= ~register_mask
                            if live_registers[register_id] == 0:
                                del live_registers[register_id]

                    if not (
                        exclude_parameter_loads
                        and isinstance(instruction, LoadArgumentPseudoInstruction)
                    ):
                        for input_register in instruction.get_input_registers_list():
                            register_id = input_register.id
                            register_mask = input_register.mask
                            if register_id in live_registers:
                                live_registers[register_id] |= register_mask
                            else:
                                live_registers[register_id] = register_mask

                    # Merge with previously determined as live registers
                    for instruction_live_register in instruction.live_registers:
                        if instruction_live_register.id in live_registers:
                            live_registers[
                                instruction_live_register.id
                            ] |= instruction_live_register.mask
                        else:
                            live_registers[instruction_live_register.id] = (
                                instruction_live_register.mask
                            )

                    instruction.live_registers = set(
                        [
                            Register.from_parts(id, mask, expand=True)
                            for (id, mask) in live_registers.items()
                        ]
                    )
                elif isinstance(instruction, LabelQuasiInstruction):
                    for entry_point in instruction.input_branches:
                        if not instructions[entry_point].is_visited:
                            instructions[entry_point].is_visited = True
                            mark_live_registers(
                                instructions, entry_point, live_registers
                            )

        exit_points = self.find_exit_points()
        for exit_point in exit_points:
            mark_live_registers(self.instructions, exit_point, set())

    def check_live_registers(self):
        pass

    def print_live_registers(self, label=""):
        """Mark this point for live register analysis.
        
        This marks the current instruction position for live register analysis
        which will be performed after all instructions are generated.
        
        Args:
            label: Optional label to identify the location in code
        """
        from nervapy.arm.instructions import Instruction

        # Find the last actual instruction object (not index, as indices can change)
        instr_obj = None
        for i in range(len(self.instructions) - 1, -1, -1):
            if isinstance(self.instructions[i], Instruction):
                instr_obj = self.instructions[i]
                break
        
        # Store the marker for later analysis (store instruction object, not index)
        self._live_register_markers.append((instr_obj, label))
    
    def _report_live_registers_at_markers(self):
        """Report live registers at all marked points.
        
        This is called after liveness analysis has been performed on all instructions.
        """
        from nervapy.arm.instructions import Instruction
        from nervapy.arm.registers import (DRegister, GeneralPurposeRegister,
                                           QRegister, SRegister)
        
        for instr_obj, label in self._live_register_markers:
            if instr_obj is None:
                print(f"Live registers {label}: No instructions yet")
                continue
            
            # Get live registers from the instruction (computed by determine_live_registers)
            live_regs = instr_obj.live_registers if hasattr(instr_obj, 'live_registers') else set()
            
            if not live_regs:
                print(f"Live registers {label}: None")
            else:
                gp_regs = [r for r in live_regs if isinstance(r, GeneralPurposeRegister)]
                s_regs = [r for r in live_regs if isinstance(r, SRegister)]
                d_regs = [r for r in live_regs if isinstance(r, DRegister)]
                q_regs = [r for r in live_regs if isinstance(r, QRegister)]
                
                def format_reg(r, reg_type):
                    """Format a register with its name if available."""
                    if r.is_virtual:
                        vreg_id = (r.number - 0x40000) >> 12
                        name = self._register_names.get(r.number, None)
                        prefix = reg_type.lower()
                        if name:
                            return f"{prefix}-vreg<{vreg_id}, {name}>"
                        else:
                            return f"{prefix}-vreg<{vreg_id}>"
                    else:
                        return str(r)
                
                print(f"Live registers {label}:")
                if gp_regs:
                    print(f"  GP ({len(gp_regs)}): {', '.join(format_reg(r, 'gp') for r in sorted(gp_regs, key=lambda x: (x.id, x.mask)))}")
                if s_regs:
                    print(f"  S ({len(s_regs)}): {', '.join(format_reg(r, 's') for r in sorted(s_regs, key=lambda x: (x.id, x.mask)))}")
                if d_regs:
                    print(f"  D ({len(d_regs)}): {', '.join(format_reg(r, 'd') for r in sorted(d_regs, key=lambda x: (x.id, x.mask)))}")
                if q_regs:
                    print(f"  Q ({len(q_regs)}): {', '.join(format_reg(r, 'q') for r in sorted(q_regs, key=lambda x: (x.id, x.mask)))}")

    # 		all_registers = self.abi.volatile_registers + list(reversed(self.abi.argument_registers)) + self.abi.callee_save_registers
    # 		available_registers = { Register.GPType: list(), Register.WMMXType: list(), Register.VFPType: list() }
    # 		for register in all_registers:
    # 			if register not in available_registers[register.regtype]:
    # 				available_registers[register.regtype].append(register)
    # 		for instruction in self.instructions:
    # 			live_registers = { Register.GPType: set(), Register.WMMXType: set(), Register.VFPType: set() }
    # 			if isinstance(instruction, Instruction):
    # 				for live_register in instruction.live_registers:
    # 					live_registers[live_register.regtype].add(live_register)
    # 				for register_type in live_registers.keys():
    # 					if len(live_registers[register_type]) > len(available_registers[register_type]):
    # 						raise ValueError("Not enough available registers to allocate live registers at instruction {0}".format(instruction))

    def determine_register_relations(self):
        from nervapy import RegisterAllocationError
        from nervapy.arm.instructions import Instruction
        from nervapy.arm.registers import (DRegister, QRegister, Register,
                                           SRegister)
        from nervapy.arm.vfpneon import (NeonLoadStoreInstruction,
                                         VFPLoadStoreMultipleInstruction)

        all_registers = (
            self.abi.volatile_registers
            + list(reversed(self.abi.argument_registers))
            + self.abi.callee_save_registers
        )
        available_registers = {
            Register.GPType: list(),
            Register.WMMXType: list(),
            Register.VFPType: list(),
        }
        for register in all_registers:
            if register.type == Register.GPType or register.type == Register.WMMXType:
                register_bitboard = 0x1 << register.get_physical_number()
                if register_bitboard not in available_registers[register.type]:
                    available_registers[register.type].append(register_bitboard)
        for instruction in self.instructions:
            if isinstance(instruction, Instruction):
                # Track all virtual registers used in the instruction (both live and outputs)
                virtual_live_registers = [
                    register
                    for register in instruction.live_registers
                    if register.is_virtual
                ]
                # Also include output registers that may not be in live_registers
                # (e.g., dead code outputs that are written but never read)
                for output_reg in instruction.get_output_registers_list():
                    if output_reg.is_virtual and output_reg not in virtual_live_registers:
                        virtual_live_registers.append(output_reg)
                
                for registerX in virtual_live_registers:
                    if registerX.type == Register.VFPType:
                        if isinstance(registerX, SRegister) and registerX.parent:
                            registerX = registerX.parent
                        if isinstance(registerX, DRegister) and registerX.parent:
                            registerX = registerX.parent
                        if registerX.get_id() not in self.allocation_options:
                            if isinstance(registerX, SRegister):
                                self.allocation_options[registerX.id] = [
                                    (0x1 << n) for n in range(32)
                                ]
                            elif isinstance(registerX, DRegister):
                                if self.target.has_vfpd32:
                                    self.allocation_options[registerX.id] = [
                                        (0x3 << n) for n in range(0, 64, 2)
                                    ]
                                else:
                                    self.allocation_options[registerX.id] = [
                                        (0x3 << n) for n in range(0, 32, 2)
                                    ]
                            else:
                                self.allocation_options[registerX.id] = [
                                    (0xF << n) for n in range(0, 64, 4)
                                ]
                    else:
                        if registerX.id not in self.allocation_options:
                            self.allocation_options[registerX.id] = list(
                                available_registers[registerX.type]
                            )

                    self.unallocated_registers.append((registerX.id, registerX.type))

                    # Setup the list of conflicting registers for each virtual register
                    if registerX.id not in self.conflicting_registers:
                        self.conflicting_registers[registerX.id] = set()
                    for registerY in virtual_live_registers:
                        # VFP registers have a conflict even they are of different size
                        if (
                            registerX.id != registerY.id
                            and registerX.type == registerY.type
                        ):
                            self.conflicting_registers[registerX.id].add(registerY.id)

        # Mark available physical registers for each virtual register
        for instruction in self.instructions:
            if isinstance(instruction, Instruction):
                virtual_live_registers = [
                    register
                    for register in instruction.live_registers
                    if register.is_virtual
                ]
                # If a physical register is live at some point, it can not be allocated for a virtual register
                physical_live_registers = [
                    register
                    for register in instruction.live_registers
                    if not register.is_virtual
                ]
                for virtual_register in virtual_live_registers:
                    for physical_register in physical_live_registers:
                        if virtual_register.type == physical_register.type:
                            virtual_register_id = virtual_register.id
                            physical_register_bitboard = physical_register.bitboard
                            self.allocation_options[virtual_register_id][:] = [
                                possible_register_bitboard
                                for possible_register_bitboard in self.allocation_options[
                                    virtual_register_id
                                ]
                                if (
                                    possible_register_bitboard
                                    & physical_register_bitboard
                                )
                                == 0
                            ]

        # Detect group constraints
        constraints = dict()
        for instruction in self.instructions:
            if isinstance(instruction, NeonLoadStoreInstruction) or isinstance(
                instruction, VFPLoadStoreMultipleInstruction
            ):
                if isinstance(instruction, NeonLoadStoreInstruction):
                    register_list = instruction.operands[0].get_registers_list()
                    physical_registers_count = 32
                else:
                    register_list = instruction.operands[1].get_registers_list()
                    physical_registers_count = 32 if self.target.has_vfpd32 else 16
                if len(register_list) > 1:
                    if all(
                        isinstance(register, DRegister) for register in register_list
                    ):
                        register_id_list = list()
                        for register in register_list:
                            register_id = register.get_id()
                            if register_id not in register_id_list:
                                register_id_list.append(register_id)
                        register_id_list = tuple(register_id_list)
                        # Iterate possible allocations for this register list
                        # For VLD1/VST1 instructions all registers must be allocated to sequential physical registers
                        options = list()
                        for sequence_bitboard_position in range(
                            0,
                            2 * physical_registers_count - 2 * len(register_list) + 2,
                            2,
                        ):
                            register_bitboards = [
                                0x3 << (sequence_bitboard_position + 2 * i)
                                for i in range(len(register_list))
                            ]
                            for i, (bitboard, register) in enumerate(
                                zip(register_bitboards, register_list)
                            ):
                                register_bitboards[i] = register.extend_bitboard(
                                    bitboard
                                )
                            # Check that bitboard is available for allocation
                            for register, bitboard in zip(
                                register_list, register_bitboards
                            ):
                                if (
                                    bitboard
                                    not in self.allocation_options[register.get_id()]
                                ):
                                    break
                            else:
                                # Check that if registers with the same id use the same bitboard in this allocation
                                register_id_map = dict()
                                for register, bitboard in zip(
                                    register_list, register_bitboards
                                ):
                                    register_id = register.get_id()
                                    if register_id in register_id_map:
                                        if register_id_map[register_id] != bitboard:
                                            break
                                    else:
                                        register_id_map[register_id] = bitboard
                                else:
                                    # Check that allocation bitboards do not overlap:
                                    allocation_bitboard = 0
                                    for bitboard in register_id_map.values():
                                        if (allocation_bitboard & bitboard) == 0:
                                            allocation_bitboard |= bitboard
                                        else:
                                            break
                                    else:
                                        ordered_bitboard_list = [
                                            register_id_map[register_id]
                                            for register_id in register_id_list
                                        ]
                                        options.append(tuple(ordered_bitboard_list))
                        if options:
                            if len(register_id_list) > 1:
                                if register_id_list in constraints:
                                    constraints[register_id_list] = tuple(
                                        [
                                            option
                                            for option in constraints[register_id_list]
                                            if option in options
                                        ]
                                    )
                                else:
                                    constraints[register_id_list] = tuple(options)
                        else:
                            raise RegisterAllocationError(
                                "Impossible virtual register combination in instruction %s"
                                % instruction
                            )
                    elif all(
                        isinstance(register, SRegister) for register in register_list
                    ) and isinstance(instruction, VFPLoadStoreMultipleInstruction):
                        register_id_list = list()
                        for register in register_list:
                            register_id = register.id
                            if register_id not in register_id_list:
                                register_id_list.append(register_id)
                        register_id_list = tuple(register_id_list)
                        # Iterate possible allocations for this register list
                        # For VLDM/VSTM instructions all registers must be allocated to sequential physical registers
                        options = list()
                        for sequence_bitboard_position in range(
                            0, 32 - len(register_list) + 1
                        ):
                            register_bitboards = [
                                0x1 << (sequence_bitboard_position + i)
                                for i in range(len(register_list))
                            ]
                            for i, (bitboard, register) in enumerate(
                                zip(register_bitboards, register_list)
                            ):
                                register_bitboards[i] = register.extend_bitboard(
                                    bitboard
                                )
                            # Check that bitboard is available for allocation
                            for register, bitboard in zip(
                                register_list, register_bitboards
                            ):
                                if bitboard not in self.allocation_options[register.id]:
                                    break
                            else:
                                # Check that if registers with the same id use the same bitboard in this allocation
                                register_id_map = dict()
                                for register, bitboard in zip(
                                    register_list, register_bitboards
                                ):
                                    register_id = register.id
                                    if register_id in register_id_map:
                                        if register_id_map[register_id] != bitboard:
                                            break
                                    else:
                                        register_id_map[register_id] = bitboard
                                else:
                                    # Check that allocation bitboards do not overlap:
                                    allocation_bitboard = 0
                                    for bitboard in register_id_map.values():
                                        if (allocation_bitboard & bitboard) == 0:
                                            allocation_bitboard |= bitboard
                                        else:
                                            break
                                    else:
                                        ordered_bitboard_list = [
                                            register_id_map[register_id]
                                            for register_id in register_id_list
                                        ]
                                        options.append(tuple(ordered_bitboard_list))
                        if options:
                            if len(register_id_list) > 1:
                                if register_id_list in constraints:
                                    constraints[register_id_list] = tuple(
                                        [
                                            option
                                            for option in constraints[register_id_list]
                                            if option in options
                                        ]
                                    )
                                else:
                                    constraints[register_id_list] = tuple(options)
                        else:
                            raise RegisterAllocationError(
                                "Impossible virtual register combination in instruction %s"
                                % instruction
                            )
                    else:
                        assert False
        report_register_constraints = False
        if report_register_constraints:
            for register_list, options in constraints.items():
                print("REGISTER CONSTRAINTS: ", map(str, register_list))
                for option in options:
                    print("\t", map(lambda t: "%016X" % t, option))

        # Merging of different groups sharing a register will be implemented here sometime

        # Check that each register id appears only once
        constrained_register_id_list = [
            register_id
            for register_id_list in constraints.keys()
            for register_id in register_id_list
        ]
        assert len(constrained_register_id_list) == len(
            set(constrained_register_id_list)
        )
        constrained_register_id_set = set(constrained_register_id_list)

        # Create a map from constrained register to constrained register group
        # 		constrained_register_map = dict()
        # 		for register_id_list in constraints.keys():
        # 			for register_id in register_id_list:
        # 				constrained_register_map[register_id] = register_id_list

        # Remove individual registers from the set of unallocated registers and add the register group instead
        for constrained_register_id in constrained_register_id_list:
            while (
                constrained_register_id,
                Register.VFPType,
            ) in self.unallocated_registers:
                self.unallocated_registers.remove(
                    (constrained_register_id, Register.VFPType)
                )
        for register_id_list in constraints.keys():
            self.unallocated_registers.append((register_id_list, Register.VFPType))

        # 		print "UNALLOCATED REGISTERS:"
        # 		print "\t", self.unallocated_registers

        # Remove individual registers from the sets of conflicting registers and add the register group instead
        # 		for register_id_list in constraints.keys():
        # 			self.conflicting_registers[register_id_list] = set()
        # 		for constrained_register_id in constrained_register_id_list:
        # 			self.conflicting_registers[constrained_register_map[constrained_register_id]].update(self.conflicting_registers[constrained_register_id])
        # 			del self.conflicting_registers[constrained_register_id]
        # 		for conflicting_registers_set in self.conflicting_registers.values():
        # 			for constrained_register_id in constrained_register_id_list:
        # 				if constrained_register_id in conflicting_registers_set:
        # 					conflicting_registers_set.remove(constrained_register_id)
        # 					conflicting_registers_set.add(constrained_register_map[constrained_register_id])

        # Remove individual registers from the lists of allocation options and add the register group instead
        for constrained_register_id in constrained_register_id_list:
            del self.allocation_options[constrained_register_id]
        for register_id_list, constrained_options in constraints.items():
            self.allocation_options[register_id_list] = list(options)

    def _get_register_type_name(self, register_type):
        """Get human-readable name for register type."""
        from nervapy.arm.registers import Register
        
        if register_type == Register.GPType:
            return "general-purpose"
        elif register_type == Register.VFPType:
            return "VFP/NEON"
        elif register_type == Register.WMMXType:
            return "WMMX"
        else:
            return "unknown type %d" % register_type

    def _get_available_registers_info(self, register_type):
        """Get information about available registers for a type."""
        from nervapy.arm.registers import Register
        
        if register_type == Register.GPType:
            # General purpose registers: r0-r12 (13 registers)
            # Note: r13 (sp), r14 (lr), r15 (pc) are special and typically not used for general allocation
            return "r0-r12 (13 registers available for allocation)"
        elif register_type == Register.VFPType:
            return "s0-s31 or d0-d31 or q0-q15 (depending on instruction)"
        elif register_type == Register.WMMXType:
            return "wr0-wr15 (16 registers)"
        else:
            return "unknown"

    def _count_virtual_registers_by_type(self, register_type):
        """Count how many virtual registers of a given type are actually being allocated (after optimization)."""
        from nervapy.arm.registers import Register

        # Count unique registers in unallocated_registers that match the given type
        # This list has already been filtered by liveness analysis
        # Use a set to avoid counting duplicates
        unique_ids = set()
        for virtual_register_id, virtual_register_type in self.unallocated_registers:
            if isinstance(virtual_register_id, tuple):
                # Register list - all registers in the list should be the same type
                if virtual_register_type == register_type:
                    unique_ids.update(virtual_register_id)
            else:
                # Single register
                if virtual_register_type == register_type:
                    unique_ids.add(virtual_register_id)
        return len(unique_ids)

    def _get_max_physical_registers(self, register_type):
        """Get the maximum number of physical registers available for a type."""
        from nervapy.arm.registers import Register
        
        if register_type == Register.GPType:
            # Typically r0-r12 can be allocated (13 registers)
            # But this can vary based on ABI and function constraints
            return 13
        elif register_type == Register.VFPType:
            # VFP/NEON: 32 single-precision (s0-s31) or 16 double-precision (d0-d15) or 8 quad (q0-q7)
            # This is a simplification - actual count depends on usage
            return 32
        elif register_type == Register.WMMXType:
            return 16
        else:
            return 0

    def allocate_registers(self):
        from nervapy.arm.instructions import Instruction
        from nervapy.arm.pseudo import LoadArgumentPseudoInstruction
        from nervapy.arm.registers import Register

        # Save counts before allocation starts (after liveness analysis has eliminated dead code)
        # This gives us accurate counts for error messages
        self._vr_counts_by_type = {}
        for reg_type in [Register.GPType, Register.VFPType, Register.WMMXType]:
            self._vr_counts_by_type[reg_type] = self._count_virtual_registers_by_type(reg_type)
        
        # Map from virtual register id to physical register
        register_allocation = dict()
        for virtual_register_id, virtual_register_type in self.unallocated_registers:
            register_allocation[virtual_register_id] = None

        def bind_register(virtual_register_id, physical_register):
            # Remove option to allocate any conflicting virtual register to the same physical register or its enclosing register
            physical_register_bitboard = physical_register.bitboard
            for conflicting_register_id in self.conflicting_registers[
                virtual_register_id
            ]:
                if conflicting_register_id in self.allocation_options:
                    for allocation_bitboard in self.allocation_options[
                        conflicting_register_id
                    ]:
                        if (allocation_bitboard & physical_register_bitboard) != 0:
                            self.allocation_options[conflicting_register_id].remove(
                                allocation_bitboard
                            )
            register_allocation[virtual_register_id] = physical_register

        def bind_registers(virtual_register_id_list, physical_register_id_list):
            # Remove option to allocate any conflicting virtual register to the same physical register or its enclosing register
            physical_register_bitboard_list = [
                physical_register.get_bitboard()
                for physical_register in physical_register_id_list
            ]
            for virtual_register_id, physical_register_bitboard in zip(
                virtual_register_id_list, physical_register_bitboard_list
            ):
                for conflicting_register_id in self.conflicting_registers[
                    virtual_register_id
                ]:
                    for (
                        allocation_key,
                        allocation_option,
                    ) in self.allocation_options.items():
                        if isinstance(allocation_key, tuple):
                            if conflicting_register_id in allocation_key:
                                conflicting_register_index = allocation_key.index(
                                    conflicting_register_id
                                )
                                for bitboard_list in allocation_option:
                                    if (
                                        bitboard_list[conflicting_register_index]
                                        & physical_register_bitboard
                                    ) != 0:
                                        allocation_option.remove(bitboard_list)
                        else:
                            if conflicting_register_id == allocation_key:
                                for bitboard in allocation_option:
                                    if (bitboard & physical_register_bitboard) != 0:
                                        allocation_option.remove(bitboard)

            for virtual_register_id, physical_register_id in zip(
                virtual_register_id_list, physical_register_id_list
            ):
                register_allocation[virtual_register_id] = physical_register_id

        def is_allocated(virtual_register_id):
            return bool(register_allocation[virtual_register_id])

        # First allocate parameters
        for instruction in self.instructions:
            if isinstance(instruction, LoadArgumentPseudoInstruction):
                if instruction.argument.register:
                    if instruction.destination.register.is_virtual:
                        if not is_allocated(instruction.destination.register.id):
                            if (
                                instruction.argument.register.bitboard
                                in self.allocation_options[
                                    instruction.destination.register.id
                                ]
                            ):
                                bind_register(
                                    instruction.destination.register.id,
                                    instruction.argument.register,
                                )

        # Now allocate registers with special restrictions
        for (
            virtual_register_id_list,
            virtual_register_type,
        ) in self.unallocated_registers:
            if isinstance(virtual_register_id_list, tuple):
                # 				print "REGLIST: ", map(str, virtual_register_id_list)
                if not self.allocation_options[virtual_register_id_list]:
                    # Use saved count from before allocation started
                    vr_count = self._vr_counts_by_type.get(virtual_register_type, 0)
                    max_phys = self._get_max_physical_registers(virtual_register_type)
                    raise RuntimeError(
                        "Register allocation failed: No available physical registers for virtual register list %s (type: %s).\n"
                        "Your code uses %d virtual %s registers, but only ~%d physical registers are available.\n"
                        "To fix: reduce the number of registers used in your Python code." 
                        % (virtual_register_id_list, self._get_register_type_name(virtual_register_type),
                           vr_count, self._get_register_type_name(virtual_register_type), max_phys)
                    )
                physical_register_bitboard_list = self.allocation_options[
                    virtual_register_id_list
                ][0]
                physcial_registers_list = [
                    Register.from_bitboard(
                        physical_register_bitboard, virtual_register_type
                    )
                    for physical_register_bitboard in physical_register_bitboard_list
                ]
                bind_registers(virtual_register_id_list, physcial_registers_list)

        # Now allocate all other registers
        while self.unallocated_registers:
            virtual_register_id, virtual_register_type = self.unallocated_registers.pop(
                0
            )
            if not isinstance(virtual_register_id, tuple):
                if not is_allocated(virtual_register_id):
                    if not self.allocation_options[virtual_register_id]:
                        # Use saved count from before allocation started
                        vr_count = self._vr_counts_by_type.get(virtual_register_type, 0)
                        max_phys = self._get_max_physical_registers(virtual_register_type)
                        
                        # Debug: find max simultaneous live registers  
                        max_live = 0
                        max_live_instr = None
                        max_live_line = None
                        max_live_idx = None
                        max_live_regs = []
                        for idx, instruction in enumerate(self.instructions):
                            if hasattr(instruction, 'live_registers'):
                                live_regs = [r for r in instruction.live_registers 
                                            if hasattr(r, 'type') and r.type == virtual_register_type and r.is_virtual]
                                live_count = len(live_regs)
                                if live_count > max_live:
                                    max_live = live_count
                                    max_live_instr = instruction
                                    max_live_idx = idx
                                    max_live_line = getattr(instruction, 'line_number', None)
                                    # Include variable names in the register representation
                                    max_live_regs = []
                                    for r in live_regs:
                                        reg_str = str(r)
                                        var_name = self._register_names.get(r.number, None)
                                        if var_name:
                                            reg_str = f"{reg_str}, {var_name}"
                                        max_live_regs.append(reg_str)
                        
                        debug_msg = ""
                        if max_live <= max_phys:
                            debug_msg = (f"\n\nPhysical registers available: {max_phys}\n"
                                       f"The register pressure ({max_live}/{max_phys}) should be manageable, but the allocator\n"
                                       f"couldn't find a valid allocation due to conflicting constraints.\n")
                            if max_live_instr is not None:
                                # Show instruction location info
                                location_info = []
                                if hasattr(max_live_instr, 'source_file') and max_live_instr.source_file:
                                    location_info.append(f"File: {max_live_instr.source_file}")
                                if hasattr(max_live_instr, 'line_number') and max_live_instr.line_number:
                                    location_info.append(f"Line: {max_live_instr.line_number}")
                                if location_info:
                                    debug_msg += f"Max register pressure at {', '.join(location_info)}\n"
                                elif max_live_idx is not None:
                                    debug_msg += f"Max register pressure at instruction #{max_live_idx} (index in generated code)\n"
                                    debug_msg += f"Hint: Enable collect_origin=True in Function() to see Python source line numbers.\n"
                                
                                debug_msg += f"Instruction with max pressure: {max_live_instr}\n"
                                
                                # Show the source code if available
                                if hasattr(max_live_instr, 'source_code') and max_live_instr.source_code:
                                    debug_msg += f"Source code: {max_live_instr.source_code}\n"
                                
                                if max_live_regs:
                                    debug_msg += f"Live virtual registers: {', '.join(sorted(max_live_regs))}\n"
                            debug_msg += f"\nThis suggests the greedy allocator made suboptimal early choices.\n"
                            debug_msg += f"Try reordering your code or reducing temporary register usage.\n"
                        else:
                            debug_msg = (f"\n\nThis exceeds the {max_phys} physical registers available.\n"
                                       f"You need to reduce the number of live registers at once.\n")
                            if max_live_instr is not None:
                                # Show instruction location info
                                location_info = []
                                if hasattr(max_live_instr, 'source_file') and max_live_instr.source_file:
                                    location_info.append(f"File: {max_live_instr.source_file}")
                                if hasattr(max_live_instr, 'line_number') and max_live_instr.line_number:
                                    location_info.append(f"Line: {max_live_instr.line_number}")
                                if location_info:
                                    debug_msg += f"Max register pressure at {', '.join(location_info)}\n"
                                elif max_live_idx is not None:
                                    debug_msg += f"Max register pressure at instruction #{max_live_idx} (index in generated code)\n"
                                    debug_msg += f"Hint: Enable collect_origin=True in Function() to see Python source line numbers.\n"
                                
                                debug_msg += f"Instruction: {max_live_instr}\n"
                                
                                # Show the source code if available
                                if hasattr(max_live_instr, 'source_code') and max_live_instr.source_code:
                                    debug_msg += f"Source code: {max_live_instr.source_code}\n"
                        
                        raise RuntimeError(
                            "Register allocation failed: No available physical registers for virtual register #%d (type: %s).\n"
                            "Your code uses %d virtual %s registers, but only ~%d physical registers are available.\n"
                            "Available %s registers: %s\n"
                            "To fix: reduce the number of registers used in your Python code.%s" 
                            % (
                                virtual_register_id, 
                                self._get_register_type_name(virtual_register_type),
                                vr_count,
                                self._get_register_type_name(virtual_register_type),
                                max_phys,
                                self._get_register_type_name(virtual_register_type),
                                self._get_available_registers_info(virtual_register_type),
                                debug_msg
                            )
                        )
                    physical_register_bitboard = self.allocation_options[
                        virtual_register_id
                    ][0]
                    physical_register = Register.from_bitboard(
                        physical_register_bitboard, virtual_register_type
                    )
                    bind_register(virtual_register_id, physical_register)

        # Verify all virtual registers used in instructions are tracked
        untracked_registers = set()
        for instruction in self.instructions:
            if isinstance(instruction, Instruction):
                for input_register in instruction.get_input_registers_list():
                    if input_register.is_virtual:
                        if input_register.id not in register_allocation:
                            untracked_registers.add(input_register.id)
                for output_register in instruction.get_output_registers_list():
                    if output_register.is_virtual:
                        if output_register.id not in register_allocation:
                            untracked_registers.add(output_register.id)
        
        if untracked_registers:
            raise RuntimeError(
                f"Internal error: Virtual registers {sorted(untracked_registers)} used in instructions "
                f"but were not tracked for allocation. This indicates a bug where registers were created "
                f"after liveness analysis or were not properly added to live_registers."
            )
        
        for instruction in self.instructions:
            if isinstance(instruction, Instruction):
                for input_register in instruction.get_input_registers_list():
                    if input_register.is_virtual:
                        input_register.bind(register_allocation[input_register.id])
                for output_register in instruction.get_output_registers_list():
                    if output_register.is_virtual:
                        output_register.bind(
                            register_allocation[output_register.id]
                        )

    # Updates information about registers to be saved/restored in the function prologue/epilogue
    def update_stack_frame(self):
        from nervapy.arm.instructions import Instruction

        for instruction in self.instructions:
            if isinstance(instruction, Instruction):
                self.stack_frame.preserve_registers(
                    instruction.get_output_registers_list()
                )

    def remove_assume_statements(self):
        from nervapy.arm.pseudo import AssumeInitializedPseudoInstruction

        new_instructions = list()
        for instruction in self.instructions:
            if isinstance(instruction, AssumeInitializedPseudoInstruction):
                continue
            else:
                new_instructions.append(instruction)
        self.instructions = new_instructions

    def generate_parameter_loads(self):
        from nervapy.arm.generic import LDR, MOV
        from nervapy.arm.pseudo import LoadArgumentPseudoInstruction
        from nervapy.arm.registers import sp

        new_instructions = list()
        for instruction in self.instructions:
            if isinstance(instruction, LoadArgumentPseudoInstruction):
                parameter = instruction.argument
                if parameter.register:
                    # If parameter is in a register, use register-register move:
                    if instruction.destination.register != parameter.register:
                        # Parameter is in a different register than instruction destination, generate move:
                        new_instruction = MOV(
                            instruction.destination.register, parameter.register
                        )
                        new_instruction.live_registers = instruction.live_registers
                        new_instruction.available_registers = (
                            instruction.available_registers
                        )
                        new_instructions.append(new_instruction)
                    # If parameter is in the same register as instruction destination, no instruction needed:
                    #   MOV( instruction.destination == parameter.register_location, parameter.register_location )
                    # is a no-op
                else:
                    parameter_address = (
                        self.stack_frame.get_parameters_offset()
                        + parameter.stack_offset
                    )
                    new_instruction = LDR(
                        instruction.destination.register, [sp, parameter_address]
                    )
                    new_instruction.live_registers = instruction.live_registers
                    new_instruction.available_registers = (
                        instruction.available_registers
                    )
                    new_instructions.append(new_instruction)
            else:
                new_instructions.append(instruction)
        self.instructions = new_instructions

    def generate_constant_loads(self):
        from nervapy import ConstantBucket
        from nervapy.arm.instructions import Instruction
        from nervapy.arm.pseudo import LoadConstantPseudoInstruction

        max_alignment = 0
        for instruction in self.instructions:
            if isinstance(instruction, Instruction):
                constant = instruction.get_constant()
                if constant is not None:
                    constant_alignment = constant.get_alignment()
                    constant_size = constant.size * constant.repeats
                    max_alignment = max(max_alignment, constant_alignment)

        constant_id = 0
        constant_label_map = dict()
        constant_buckets = dict()
        for instruction in self.instructions:
            if isinstance(instruction, Instruction):
                constant = instruction.get_constant()
                if constant is not None:
                    if constant in constant_label_map:
                        constant.label = constant_label_map[constant]
                    else:
                        constant.label = "c" + str(constant_id)
                        constant_id += 1
                        constant_label_map[constant] = constant.label
                        constant_alignment = constant.get_alignment()
                        constant_size = constant.size * constant.repeats
                        if constant_alignment in constant_buckets:
                            constant_buckets[constant_alignment].add(constant)
                            if constant_buckets[constant_alignment].is_full():
                                del constant_buckets[constant_alignment]
                        else:
                            constant_bucket = ConstantBucket(max_alignment / 8)
                            constant_bucket.add(constant)
                            self.constants.append(constant_bucket)
                            if not constant_bucket.is_full():
                                constant_buckets[constant_alignment] = constant_bucket

        new_instructions = list()
        for instruction in self.instructions:
            if isinstance(instruction, LoadConstantPseudoInstruction):
                raise NotImplementedError()
            else:
                new_instructions.append(instruction)
        self.instructions = new_instructions

    def validate_stack_alignment_check(self):
        """
        Validate that stack is 8-byte aligned before BL/BLX instructions.

        For ARMv7-M architecture (Cortex-M), the AAPCS requires that the stack
        pointer must be 8-byte aligned at any public interface (function calls).
        This method tracks stack pointer changes and validates alignment before
        BL and BLX instructions.
        """
        from nervapy.arm.generic import (ArithmeticInstruction,
                                         BranchLinkExchangeInstruction,
                                         BranchWithLinkInstruction,
                                         PushPopInstruction,
                                         StoreMultipleInstruction)
        from nervapy.arm.instructions import Instruction
        from nervapy.arm.isa import Extension
        from nervapy.arm.registers import sp

        # Enforce for ARMv7-M and ARMv8-M architectures (V8MMain implies V7M via prerequisites)
        if (
            Extension.V7M not in self.target.extensions
            and Extension.V8MBase not in self.target.extensions
        ):
            return

        # Track stack offset from initial 8-byte aligned position
        # The prologue is generated by generate_prolog_and_epilog() which inserts
        # instructions after the ENTRY label. These are guaranteed to maintain
        # 8-byte alignment. We need to skip them when tracking.
        #
        # Strategy: Count prologue size, then skip that many PUSH/VPUSH/STMDB instructions
        # at the start of the function.
        prologue_size = len(self.stack_frame.generate_prologue())
        prologue_instructions_seen = 0
        stack_offset = 0

        for instruction in self.instructions:
            if not isinstance(instruction, Instruction):
                continue

            # Skip prologue instructions (PUSH/VPUSH/STMDB/SUB-sp at start of function)
            if prologue_instructions_seen < prologue_size:
                if isinstance(instruction, PushPopInstruction) and instruction.name in (
                    "PUSH",
                    "PUSH.W",
                ):
                    prologue_instructions_seen += 1
                    continue
                # Also check for VPUSH (VFP register saves)
                elif instruction.__class__.__name__ == "VfpNeonPushPopInstruction":
                    prologue_instructions_seen += 1
                    continue
                # Also check for STMDB (used with high registers)
                elif isinstance(instruction, StoreMultipleInstruction):
                    if instruction.writeback and instruction.name.startswith("STM"):
                        prologue_instructions_seen += 1
                        continue
                # Also skip SUB sp, sp, #imm used for alignment padding
                elif isinstance(instruction, ArithmeticInstruction):
                    if len(instruction.operands) >= 3:
                        dest = instruction.operands[0]
                        src1 = instruction.operands[1]
                        if (
                            hasattr(dest, "register")
                            and dest.register == sp
                            and hasattr(src1, "register")
                            and src1.register == sp
                            and instruction.name.startswith("SUB")
                        ):
                            prologue_instructions_seen += 1
                            continue

            # Track PUSH instructions (user code)
            if isinstance(instruction, PushPopInstruction):
                if instruction.name in ("PUSH", "PUSH.W"):
                    # Each register pushes 4 bytes
                    num_registers = len(instruction.operands[0].get_registers_list())
                    stack_offset += num_registers * 4
                elif instruction.name in ("POP", "POP.W"):
                    # Each register pops 4 bytes
                    num_registers = len(instruction.operands[0].get_registers_list())
                    stack_offset -= num_registers * 4

            # Track STMDB/LDMIA instructions that modify SP
            elif isinstance(instruction, StoreMultipleInstruction):
                if instruction.writeback:
                    base_reg = instruction.operands[0]
                    # Check if base register is SP
                    if hasattr(base_reg, "register") and base_reg.register == sp:
                        num_registers = len(
                            instruction.operands[1].get_registers_list()
                        )
                        if instruction.name.startswith("STM"):
                            stack_offset += num_registers * 4
                        elif instruction.name.startswith("LDM"):
                            stack_offset -= num_registers * 4

            # Track SUB/ADD with SP
            elif isinstance(instruction, ArithmeticInstruction):
                if len(instruction.operands) >= 3:
                    dest = instruction.operands[0]
                    src1 = instruction.operands[1]
                    src2 = instruction.operands[2]

                    # Check if destination is SP
                    if (
                        hasattr(dest, "register")
                        and dest.register == sp
                        and hasattr(src1, "register")
                        and src1.register == sp
                    ):

                        # Get immediate value (check both 'immediate' and 'value')
                        imm_value = None
                        if hasattr(src2, "immediate"):
                            imm_value = src2.immediate
                        elif hasattr(src2, "value"):
                            imm_value = src2.value

                        if imm_value is not None:
                            if instruction.name.startswith("SUB"):
                                # SUB sp, sp, #imm - allocates stack space
                                stack_offset += imm_value
                            elif instruction.name.startswith("ADD"):
                                # ADD sp, sp, #imm - deallocates stack space
                                stack_offset -= imm_value

            # Check alignment before BL/BLX
            elif isinstance(
                instruction, (BranchWithLinkInstruction, BranchLinkExchangeInstruction)
            ):
                if stack_offset % 8 != 0:
                    raise ValueError(
                        "Stack is not 8-byte aligned before {0} instruction.\n"
                        "Current stack offset: {1} bytes (misaligned by {2} bytes).\n"
                        "ARMv7-M/ARMv8-M requires 8-byte stack alignment at function calls (AAPCS requirement).\n"
                        "Add registers in pairs to PUSH instructions or adjust the stack manually to maintain alignment.".format(
                            instruction.name, stack_offset, stack_offset % 8
                        )
                    )

    def optimize_instructions(self):
        from nervapy.arm.generic import MovInstruction
        from nervapy.arm.vfpneon import VfpNeonMovInstruction

        new_instructions = list()
        for instruction in self.instructions:
            # Remove moves where source and destination are the same

            if isinstance(instruction, VfpNeonMovInstruction):
                if instruction.operands[0] != instruction.operands[1]:
                    new_instructions.append(instruction)
            else:
                new_instructions.append(instruction)
        self.instructions = new_instructions

    def get_target(self):
        return self.target

    @property
    def isa_extensions(self):
        from nervapy.arm.instructions import Instruction
        from nervapy.arm.isa import Extension, Extensions
        from nervapy.arm.registers import DRegister, QRegister

        # Start with the target microarchitecture's extensions
        isa_extensions = Extensions(*self.target.extensions)
        for instruction in self.instructions:
            if isinstance(instruction, Instruction):
                for extension in instruction.isa_extensions:
                    isa_extensions += extension
                if any(
                    isinstance(register, QRegister)
                    or isinstance(register, DRegister)
                    and register.is_extended
                    for register in instruction.get_registers_list()
                ):
                    isa_extensions += Extension.VFPd32
        return isa_extensions

    def get_yeppp_isa_extensions(self):
        isa_extensions_map = {
            "V4": ("V4", None, None),
            "V5": ("V5", None, None),
            "V5E": ("V5E", None, None),
            "V6": ("V6", None, None),
            "V6K": ("V6K", None, None),
            "V7": ("V7", None, None),
            "V7MP": ("V7MP", None, None),
            "Div": ("Div", None, None),
            "Thumb": ("Thumb", None, None),
            "Thumb2": ("Thumb2", None, None),
            "VFP": ("VFP", None, None),
            "VFP2": ("VFP2", None, None),
            "VFP3": ("VFP3", None, None),
            "VFPd32": ("VFPd32", None, None),
            "VFP3HP": ("VFP3HP", None, None),
            "VFP4": ("VFP4", None, None),
            "VFPVectorMode": (None, None, "VFPVectorMode"),
            "XScale": (None, "XScale", None),
            "WMMX": (None, "WMMX", None),
            "WMMX2": (None, "WMMX2", None),
            "NEON": (None, "NEON", None),
            "NEONHP": (None, "NEONHP", None),
            "NEON2": (None, "NEON2", None),
        }
        isa_extensions, simd_extensions, system_extensions = (set(), set(), set())
        for isa_extension in self.get_isa_extensions():
            if isa_extension is not None:
                isa_extension, simd_extension, system_extension = isa_extensions_map[
                    isa_extension
                ]
                if isa_extension is not None:
                    isa_extensions.add(isa_extension)
                if simd_extension is not None:
                    simd_extensions.add(simd_extension)
                if system_extension is not None:
                    system_extensions.add(system_extension)
        isa_extensions = map(lambda id: "YepARMIsaFeature" + id, isa_extensions)
        if not isa_extensions:
            isa_extensions = ["YepIsaFeaturesDefault"]
        simd_extensions = map(lambda id: "YepARMSimdFeature" + id, simd_extensions)
        if not simd_extensions:
            simd_extensions = ["YepSimdFeaturesDefault"]
        system_extensions = map(
            lambda id: "YepARMSystemFeature" + id, system_extensions
        )
        if not system_extensions:
            system_extensions = ["YepSystemFeaturesDefault"]
        return (isa_extensions, simd_extensions, system_extensions)

    def allocate_local_variable(self):
        self.local_variables_count += 1
        return self.local_variables_count

    def allocate_q_register(self):
        self.virtual_registers_count += 1
        register_number = (self.virtual_registers_count << 12) | 0x0F0
        
        # Try to capture variable name from caller's frame
        try:
            import inspect
            frame = inspect.currentframe().f_back.f_back
            if frame:
                import linecache
                line = linecache.getline(frame.f_code.co_filename, frame.f_lineno).strip()
                if '=' in line and 'QRegister' in line:
                    var_name = line.split('=')[0].strip()
                    if var_name and not var_name.startswith('#'):
                        self._register_names[register_number] = var_name
        except:
            pass
        
        return register_number

    def allocate_d_register(self):
        self.virtual_registers_count += 1
        return (self.virtual_registers_count << 12) | 0x300

    def allocate_s_register(self):
        self.virtual_registers_count += 1
        return (self.virtual_registers_count << 12) | 0x400

    def allocate_wmmx_register(self):
        self.virtual_registers_count += 1
        return (self.virtual_registers_count << 12) | 0x002

    def allocate_general_purpose_register(self):
        self.virtual_registers_count += 1
        register_number = (self.virtual_registers_count << 12) | 0x001
        
        # Try to capture variable name from caller's frame
        try:
            import inspect
            frame = inspect.currentframe().f_back.f_back  # Go up 2 frames: this -> __init__ -> caller
            if frame:
                # Get the line of code being executed
                import linecache
                line = linecache.getline(frame.f_code.co_filename, frame.f_lineno).strip()
                # Simple pattern matching for "varname = GeneralPurposeRegister()"
                if '=' in line and 'GeneralPurposeRegister' in line:
                    var_name = line.split('=')[0].strip()
                    if var_name and not var_name.startswith('#'):
                        self._register_names[register_number] = var_name
        except:
            pass  # If name capture fails, just continue without name
        
        return register_number

    def allocate_p_register(self):
        self.virtual_registers_count += 1
        return (self.virtual_registers_count << 12) | 0x001


class LocalVariable(object):
    def __init__(self, register_type):
        from nervapy.arm.registers import (DRegister, GeneralPurposeRegister,
                                           QRegister, SRegister, WMMXRegister)

        super(LocalVariable, self).__init__()
        if isinstance(register_type, int):
            self.size = register_type
        elif register_type == GeneralPurposeRegister:
            self.size = 4
        elif register_type == WMMXRegister:
            self.size = 8
        elif register_type == SRegister:
            self.size = 4
        elif register_type == DRegister:
            self.size = 8
        elif register_type == QRegister:
            self.size = 16
        else:
            raise ValueError("Unsupported register type {0}".format(register_type))
        self.id = active_function.allocate_local_variable()
        self.address = None
        self.offset = 0
        self.parent = None

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        if self.is_subvariable():
            address = self.parent.get_address()
            if address is not None:
                address += self.offset
        else:
            address = self.address
        if address is not None:
            return "[{0}]".format(address)
        else:
            return "local-variable<{0}>".format(self.id)

    def is_subvariable(self):
        return self.parent is not None

    def get_parent(self):
        return self.parent

    def get_root(self):
        if self.is_subvariable():
            return self.get_parent().get_root()
        else:
            return self

    def get_address(self):
        if self.is_subvariable():
            return self.parent.get_address() + self.offset
        else:
            return self.address

    def get_size(self):
        return self.size

    def get_low(self):
        assert self.get_size() % 2 == 0
        child = LocalVariable(self.get_size() / 2)
        child.parent = self
        child.offset = 0
        return child

    def get_high(self):
        assert self.get_size() % 2 == 0
        child = LocalVariable(self.get_size() / 2)
        child.parent = self
        child.offset = self.get_size() / 2
        return child


class StackFrame(object):
    def __init__(self, abi):
        super(StackFrame, self).__init__()
        self.abi = abi
        self.general_purpose_registers = list()
        self.d_registers = list()
        self.s_variables = list()
        self.d_variables = list()
        self.q_variables = list()

    def preserve_registers(self, registers):
        for register in registers:
            self.preserve_register(register)

    def preserve_register(self, register):
        from nervapy.arm.registers import (DRegister, GeneralPurposeRegister,
                                           QRegister, SRegister)

        if isinstance(register, GeneralPurposeRegister):
            if not register in self.general_purpose_registers:
                if register in self.abi.callee_save_registers:
                    self.general_purpose_registers.append(register)
        elif isinstance(register, SRegister):
            if not register.is_virtual():
                register = register.get_parent()
                if not register in self.d_registers:
                    if register in self.abi.callee_save_registers:
                        self.d_registers.append(register)
        elif isinstance(register, DRegister):
            if not register in self.d_registers:
                if register in self.abi.callee_save_registers:
                    self.d_registers.append(register)
        elif isinstance(register, QRegister):
            d_low = register.get_low_part()
            d_high = register.get_high_part()
            if d_low not in self.d_registers:
                if register in self.abi.callee_save_registers:
                    self.d_registers.append(d_low)
            if d_high not in self.d_registers:
                if register in self.abi.callee_save_registers:
                    self.d_registers.append(d_high)
        else:
            raise TypeError("Unsupported register type {0}".format(type(register)))

    def force_preserve_register(self, register):
        """Add *register* to the preservation list unconditionally (no ABI check)."""
        from nervapy.arm.registers import (DRegister, GeneralPurposeRegister,
                                           QRegister, SRegister)

        if isinstance(register, GeneralPurposeRegister):
            if register not in self.general_purpose_registers:
                self.general_purpose_registers.append(register)
        elif isinstance(register, SRegister):
            if not register.is_virtual():
                register = register.get_parent()
                if register not in self.d_registers:
                    self.d_registers.append(register)
        elif isinstance(register, DRegister):
            if register not in self.d_registers:
                self.d_registers.append(register)
        elif isinstance(register, QRegister):
            d_low = register.get_low_part()
            d_high = register.get_high_part()
            if d_low not in self.d_registers:
                self.d_registers.append(d_low)
            if d_high not in self.d_registers:
                self.d_registers.append(d_high)
        else:
            raise TypeError("Unsupported register type {0}".format(type(register)))

    def add_variable(self, variable):
        if variable.get_size() == 16:
            if variable not in self.sse_variables:
                self.sse_variables.append(variable)
        elif variable.get_size() == 32:
            if variable not in self.avx_variables:
                self.avx_variables.append(variable)
        else:
            raise TypeError("Unsupported variable type {0}".format(type(variable)))

    def get_parameters_offset(self):
        parameters_offset = len(self.general_purpose_registers) * 4
        if parameters_offset % 8 == 4:
            parameters_offset += 4
        return parameters_offset + len(self.d_registers) * 8

    def generate_prologue(self):
        from nervapy.arm.formats import HighRegisterStrategy
        from nervapy.arm.generic import PUSH, PUSH_W, STMDB, SUB
        from nervapy.arm.isa import Extension
        from nervapy.arm.registers import sp
        from nervapy.arm.vfpneon import VPUSH
        from nervapy.stream import InstructionStream

        with InstructionStream() as instructions:
            if self.general_purpose_registers:
                general_purpose_registers = list(self.general_purpose_registers)

                # Check if we're targeting ARMv7-M (Cortex-M) processors
                function = self.get_function()
                is_armv7m = function and Extension.V7M in function.target.extensions

                if is_armv7m:
                    low_registers = [
                        reg
                        for reg in general_purpose_registers
                        if reg.get_physical_number() <= 7
                    ]
                    high_registers = [
                        reg
                        for reg in general_purpose_registers
                        if reg.get_physical_number() > 7
                    ]

                    if high_registers:
                        # Merge low and high into one instruction so the
                        # prologue is a single PUSH.W / STMDB covering all
                        # callee-saved registers.
                        all_registers = low_registers + high_registers
                        needs_pad = len(all_registers) % 2 == 1
                        sorted_regs = tuple(
                            sorted(
                                all_registers,
                                key=lambda reg: reg.get_physical_number(),
                            )
                        )
                        strategy = function.high_register_strategy
                        if strategy == HighRegisterStrategy.STMDB or (
                            strategy == HighRegisterStrategy.AUTO
                            and function.assembly_format.name == "ARMCC"
                        ):
                            STMDB(sp, sorted_regs)
                        else:
                            PUSH_W(sorted_regs)
                        if needs_pad:
                            SUB(sp, sp, 4)
                    elif low_registers:
                        # Only low registers - use efficient 16-bit PUSH
                        needs_pad = len(low_registers) % 2 == 1
                        PUSH(
                            tuple(
                                sorted(
                                    low_registers,
                                    key=lambda reg: reg.get_physical_number(),
                                )
                            )
                        )
                        if needs_pad:
                            SUB(sp, sp, 4)
                else:
                    # Standard ARM (non-Cortex-M) handling
                    needs_pad = len(general_purpose_registers) % 2 == 1
                    PUSH(
                        tuple(
                            sorted(
                                general_purpose_registers,
                                key=lambda reg: reg.get_physical_number(),
                            )
                        )
                    )
                    if needs_pad:
                        SUB(sp, sp, 4)

            if self.d_registers:
                VPUSH(
                    tuple(
                        sorted(
                            self.d_registers, key=lambda reg: reg.get_physical_number()
                        )
                    )
                )
        return list(iter(instructions))

    def generate_epilogue(self):
        from nervapy.arm.formats import HighRegisterStrategy
        from nervapy.arm.generic import ADD, LDMIA, POP, POP_W
        from nervapy.arm.isa import Extension
        from nervapy.arm.registers import sp
        from nervapy.arm.vfpneon import VPOP
        from nervapy.stream import InstructionStream

        with InstructionStream() as instructions:
            if self.d_registers:
                VPOP(
                    tuple(
                        sorted(
                            self.d_registers, key=lambda reg: reg.get_physical_number()
                        )
                    )
                )

            if self.general_purpose_registers:
                general_purpose_registers = list(self.general_purpose_registers)

                # Check if we're targeting ARMv7-M (Cortex-M) processors
                function = self.get_function()
                is_armv7m = function and Extension.V7M in function.target.extensions

                if is_armv7m:
                    low_registers = [
                        reg
                        for reg in general_purpose_registers
                        if reg.get_physical_number() <= 7
                    ]
                    high_registers = [
                        reg
                        for reg in general_purpose_registers
                        if reg.get_physical_number() > 7
                    ]

                    if high_registers:
                        # Mirror of prologue: one instruction restoring all regs
                        all_registers = low_registers + high_registers
                        needs_pad = len(all_registers) % 2 == 1
                        sorted_regs = tuple(
                            sorted(
                                all_registers,
                                key=lambda reg: reg.get_physical_number(),
                            )
                        )
                        strategy = function.high_register_strategy
                        if needs_pad:
                            ADD(sp, sp, 4)
                        if strategy == HighRegisterStrategy.STMDB or (
                            strategy == HighRegisterStrategy.AUTO
                            and function.assembly_format.name == "ARMCC"
                        ):
                            LDMIA(sp, sorted_regs)
                        else:
                            POP_W(sorted_regs)
                    elif low_registers:
                        # Only low registers - use efficient 16-bit POP
                        needs_pad = len(low_registers) % 2 == 1
                        if needs_pad:
                            ADD(sp, sp, 4)
                        POP(
                            tuple(
                                sorted(
                                    low_registers,
                                    key=lambda reg: reg.get_physical_number(),
                                )
                            )
                        )
                else:
                    # Standard ARM (non-Cortex-M) handling
                    needs_pad = len(general_purpose_registers) % 2 == 1
                    if needs_pad:
                        ADD(sp, sp, 4)
                    POP(
                        tuple(
                            sorted(
                                general_purpose_registers,
                                key=lambda reg: reg.get_physical_number(),
                            )
                        )
                    )
        return list(iter(instructions))

    def get_function(self):
        """Get the active function that owns this stack frame."""
        from nervapy.arm.function import active_function

        return active_function


def print_live_registers(label=""):
    """Print live registers at the current point in code generation.
    
    This function can be called from within a Function context to inspect
    which registers are currently live (i.e., their values will be used later).
    
    Note: Live register information is computed during function compilation,
    so this will show an approximation based on instructions emitted so far.
    
    Args:
        label: Optional label to identify the location in code
        
    Example:
        with Function("my_func", args, ...):
            t0 = GeneralPurposeRegister()
            ADD(t0, r0, r1)
            print_live_registers("after ADD")  # Shows which regs are live
    """
    global active_function
    if active_function is None:
        print(f"Live registers {label}: No active function")
        return
    
    active_function.print_live_registers(label)
