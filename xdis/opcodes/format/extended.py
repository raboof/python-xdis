# (C) Copyright 2023-2024 by Rocky Bernstein
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
Routines for formatting opcodes.
"""
from xdis.opcodes.format.basic import format_IS_OP, format_RAISE_VARARGS_older


def extended_format_binary_op(opc, instructions, fmt_str):
    """
    General routine for formatting binary operations.
    A binary operations pops a two arguments off of the evaluation stack and
    pushes a single value back on the evaluation stack. Also, the instruction
    must not raise an exception and must control must flow to the next instruction.

    instructions is a list of instructions
    fmt_str is a format string that indicates the two arguments.

    the return constins the string that should be added to tos_str and
    the position in instructions of the first instruction where that contributes
    to the binary operation, that is the logical beginning instruction.
    """
    i = skip_cache(instructions, 1)
    stack_inst1 = instructions[i]
    arg1 = None

    # If stack_inst1 is a jump target, then its predecessor stack_inst2
    # is possibly one of two values.
    if not stack_inst1.is_jump_target:
        if stack_inst1.tos_str is not None:
            arg1 = stack_inst1.tos_str
        if arg1 is not None or stack_inst1.opcode in opc.operator_set:
            if arg1 is None:
                arg1 = stack_inst1.argrepr
            arg1_start_offset = stack_inst1.start_offset
            if arg1_start_offset is not None:
                i = get_instruction_index_from_offset(
                    arg1_start_offset, instructions, 1
                )
                if i is None:
                    return "", None
            j = skip_cache(instructions, i + 1)
            stack_inst2 = instructions[j]
            if (
                stack_inst1.opcode in opc.operator_set
                and stack_inst2.opcode in opc.operator_set
                and not stack_inst2.is_jump_target
            ):
                arg2 = get_instruction_arg(stack_inst2, stack_inst2.argrepr)
                start_offset = stack_inst2.start_offset
                return fmt_str % (arg2, arg1), start_offset
            elif stack_inst2.start_offset is not None:
                start_offset = stack_inst2.start_offset
                arg2 = get_instruction_arg(stack_inst2, stack_inst2.argrepr)
                if arg2 == "":
                    arg2 = "..."
                return fmt_str % (arg2, arg1), start_offset
            else:
                return fmt_str % ("...", arg1), None
    return "", None


def extended_format_infix_binary_op(opc, instructions, op_str):
    """ """
    i = 1
    # 3.11+ has CACHE instructions
    while instructions[i].opname == "CACHE":
        i += 1
    stack_arg1 = instructions[i]
    arg1 = None
    if stack_arg1.tos_str is not None:
        arg1 = stack_arg1.tos_str
    if arg1 is not None or stack_arg1.opcode in opc.operator_set:
        if arg1 is None:
            arg1 = instructions[1].argrepr
        else:
            arg1 = "(%s)" % arg1
        arg1_start_offset = instructions[1].start_offset
        if arg1_start_offset is not None:
            i = get_instruction_index_from_offset(arg1_start_offset, instructions, 1)
            if i is None:
                return "", None
        j = i + 1
        # 3.11+ has CACHE instructions
        while instructions[j].opname == "CACHE":
            j += 1
        if (
            instructions[j].opcode in opc.operator_set
            and instructions[i].opcode in opc.operator_set
        ):
            if instructions[j].tos_str is not None:
                arg2 = instructions[j].tos_str
            else:
                arg2 = instructions[j].argrepr
            start_offset = instructions[j].start_offset
            return "%s%s%s" % (arg2, op_str, arg1), start_offset
        elif instructions[j].start_offset is not None:
            start_offset = instructions[j].start_offset
            if instructions[j].tos_str:
                arg2 = instructions[j].tos_str
            else:
                arg2 = instructions[j].argrepr
            if arg2 == "":
                arg2 = "..."
            else:
                arg2 = "(%s)" % arg2
            return "%s%s%s" % (arg2, op_str, arg1), start_offset
        else:
            return "...%s%s" % (op_str, arg1), None
    return "", None


def extended_format_store_op(opc, instructions):
    inst = instructions[0]

    # If the store instruction is a jump target, then
    # the previous instruction is ambiguous. Here, things
    # are more complicated, so let's not try to figure this out.
    # This kind of things is best left for a decompiler.
    if inst.is_jump_target:
        return "", None

    prev_inst = instructions[1]
    start_offset = prev_inst.offset
    if prev_inst.opcode in opc.operator_set:
        if prev_inst.opcode in opc.nullaryloadop:
            argval = safe_repr(prev_inst.argval)
        elif (
            prev_inst.opcode in opc.VARGS_OPS | opc.NARGS_OPS
            and prev_inst.tos_str is None
        ):
            # In variable arguments lists and function-like calls
            # argval is a count. So we need a TOS representation
            # to do something here.
            return "", start_offset
        else:
            argval = prev_inst.argval

        argval = get_instruction_arg(prev_inst, argval)
        start_offset = prev_inst.start_offset
        if prev_inst.opname.startswith("INPLACE_"):
            # Inplace operators have their own assign routine.
            return argval, start_offset
        return "%s = %s" % (inst.argval, argval), start_offset

    return "", start_offset


def extended_format_ternary_op(opc, instructions, fmt_str):
    """
    General routine for formatting ternary operations.
    A ternary operations pops a three arguments off of the evaluation stack and
    pushes a single value back on the evaluation stack. Also, the instruction
    must not raise an exception and must control must flow to the next instruction.

    instructions is a list of instructions
    fmt_str is a format string that indicates the two arguments.

    the return constins the string that should be added to tos_str and
    the position in instructions of the first instruction where that contributes
    to the binary operation, that is the logical beginning instruction.
    """
    i = skip_cache(instructions, 1)
    stack_inst1 = instructions[i]
    arg1 = None
    if stack_inst1.tos_str is not None:
        arg1 = stack_inst1.tos_str
    if arg1 is not None or stack_inst1.opcode in opc.operator_set:
        if arg1 is None:
            arg1 = stack_inst1.argrepr
        arg1_start_offset = stack_inst1.start_offset
        if arg1_start_offset is not None:
            i = get_instruction_index_from_offset(arg1_start_offset, instructions, 1)
            if i is None:
                return "", None
        j = skip_cache(instructions, i + 1)
        stack_inst2 = instructions[j]
        if (
            stack_inst1.opcode in opc.operator_set
            and stack_inst2.opcode in opc.operator_set
            and not stack_inst2.is_jump_target
        ):
            arg2 = get_instruction_arg(stack_inst2, stack_inst2.argrepr)
            k = skip_cache(instructions, j + 1)
            stack_inst3 = instructions[k + 1]
            start_offset = stack_inst3.start_offset
            if (
                stack_inst3.opcode in opc.operator_set
                and not stack_inst3.is_jump_target
            ):
                arg3 = get_instruction_arg(stack_inst3, stack_inst3.argrepr)
                return fmt_str % (arg2, arg1, arg3), start_offset
            else:
                arg3 = "..."
                return fmt_str % (arg2, arg1, arg3), start_offset

        elif stack_inst2.start_offset is not None and not stack_inst2.is_jump_target:
            start_offset = stack_inst2.start_offset
            arg2 = get_instruction_arg(stack_inst2, stack_inst2.argrepr)
            if arg2 == "":
                arg2 = "..."
            arg3 = "..."
            return fmt_str % (arg2, arg1, arg3), start_offset
        else:
            return fmt_str % ("...", "...", "..."), None
    return "", None


def extended_format_STORE_SUBSCR(opc, instructions):
    return extended_format_ternary_op(
        opc,
        instructions,
        "%s[%s] = %s",
    )


def extended_format_unary_op(opc, instructions, fmt_str):
    stack_arg = instructions[1]
    start_offset = instructions[1].start_offset
    if stack_arg.tos_str is not None and not stack_arg.is_jump_target:
        return fmt_str % stack_arg.tos_str, start_offset
    if stack_arg.opcode in opc.operator_set:
        return fmt_str % stack_arg.argrepr, start_offset
    return "", None


def extended_format_ATTR(opc, instructions):
    """
    Handles both LOAD_ATTR and STORE_ATTR
    """
    instr1 = instructions[1]
    if (
        instr1.tos_str
        or instr1.opcode in opc.NAME_OPS | opc.CONST_OPS | opc.LOCAL_OPS | opc.FREE_OPS
    ):
        base = get_instruction_arg(instr1)

        return (
            "%s.%s" % (base, instructions[0].argrepr),
            instructions[1].offset,
        )
    return "", None


def extended_format_BINARY_ADD(opc, instructions):
    return extended_format_infix_binary_op(opc, instructions, " + ")


def extended_format_BINARY_AND(opc, instructions):
    return extended_format_infix_binary_op(opc, instructions, " & ")


def extended_format_BINARY_FLOOR_DIVIDE(opc, instructions):
    return extended_format_infix_binary_op(opc, instructions, " // ")


def extended_format_BINARY_LSHIFT(opc, instructions):
    return extended_format_infix_binary_op(opc, instructions, " << ")


def extended_format_BINARY_MODULO(opc, instructions):
    return extended_format_infix_binary_op(opc, instructions, " % ")


def extended_format_BINARY_MULTIPLY(opc, instructions):
    return extended_format_infix_binary_op(opc, instructions, " * ")


def extended_format_BINARY_OR(opc, instructions):
    return extended_format_infix_binary_op(opc, instructions, " | ")


def extended_format_BINARY_POWER(opc, instructions):
    return extended_format_infix_binary_op(opc, instructions, " ** ")


def extended_format_BINARY_RSHIFT(opc, instructions):
    return extended_format_infix_binary_op(opc, instructions, " >> ")


def extended_format_BINARY_SUBSCR(opc, instructions):
    return extended_format_binary_op(
        opc,
        instructions,
        "%s[%s]",
    )


def extended_format_BINARY_SUBTRACT(opc, instructions):
    return extended_format_infix_binary_op(opc, instructions, " - ")


def extended_format_BINARY_TRUE_DIVIDE(opc, instructions):
    return extended_format_infix_binary_op(opc, instructions, " / ")


def extended_format_BINARY_XOR(opc, instructions):
    return extended_format_infix_binary_op(opc, instructions, " ^ ")


def extended_format_build_tuple_or_list(
    opc, instructions, left_delim, right_delim
):
    arg_count = instructions[0].argval
    is_tuple = left_delim == "("
    if arg_count == 0:
        # Note: caller generally handles this when the below isn't right.
        return "%s%s" % (left_delim, right_delim), instructions[0].offset
    arglist, _, i = get_arglist(instructions, 0, arg_count)
    if arglist is not None:
        assert isinstance(i, int)
        args_str = ", ".join(reversed(arglist))
        if arg_count == 1 and is_tuple:
            return (
                "%s%s,%s" % (left_delim, args_str, right_delim),
                instructions[i].start_offset,
            )
        else:
            return (
                "%s%s%s" % (left_delim, args_str, right_delim),
                instructions[i].start_offset,
            )
    return "", None


def extended_format_BUILD_CONST_KEY_MAP(opc, instructions):
    arg_count = instructions[0].argval
    if arg_count == 0:
        # Note: caller generally handles this when the below isn't right.
        return "{}", instructions[0].offset
    assert len(instructions) > 0
    key_tuple = instructions[1]
    key_values = key_tuple.argval
    if key_tuple.opname == "LOAD_CONST" and isinstance(key_values, tuple):
        arglist, _, i = get_arglist(instructions, 1, arg_count)
        if arglist is not None:
            assert isinstance(i, int)
            assert len(arglist) == len(key_values)
            arg_pairs = []
            for i in range(len(arglist)):
                arg_pairs.append("%s: %s" % (key_values[i], arglist[i]))
            args_str = ", ".join(arg_pairs)
            return "{" + args_str + "}", instructions[i].start_offset
    return "", None


def extended_format_BUILD_LIST(opc, instructions):
    return extended_format_build_tuple_or_list(opc, instructions, "[", "]")


def extended_format_BUILD_SET(opc, instructions):
    if instructions[0].argval == 0:
        # Degenerate case
        return "set()", instructions[0].start_offset
    return extended_format_build_tuple_or_list(opc, instructions, "{", "}")


def extended_format_BUILD_SLICE(opc, instructions):
    argc = instructions[0].argval

    assert argc in (2, 3)
    arglist, arg_count, i = get_arglist(instructions, 0, argc)
    if arg_count == 0:
        assert isinstance(i, int)
        arglist = []
        for arg in arglist:
            if arg == "None":
                arglist.append("")
            else:
                arglist.append(arg)
        return ":".join(reversed(arglist)), instructions[i].start_offset

    if instructions[0].argval == 0:
        # Degenerate case
        return "set()", instructions[0].start_offset
    return "", None


def extended_format_BUILD_TUPLE(opc, instructions):
    arg_count = instructions[0].argval
    if arg_count == 0:
        return "tuple()", instructions[0].start_offset
    return extended_format_build_tuple_or_list(opc, instructions, "(", ")")


def extended_format_COMPARE_OP(opc, instructions):
    return extended_format_infix_binary_op(
        opc,
        instructions,
        " %s " % instructions[0].argval,
    )


def extended_format_CALL_FUNCTION(opc, instructions):
    """call_function_inst should be a "CALL_FUNCTION" instruction. Look in
    `instructions` to see if we can find a method name.  If not we'll
    return None.

    """
    # From opcode description: arg_count indicates the total number of
    # positional and keyword arguments.

    call_inst = instructions[0]
    arg_count = call_inst.argval
    s = ""

    arglist, arg_count, i = get_arglist(instructions, 0, arg_count)

    if arglist is None:
        return "", None

    assert i is not None
    if i >= len(instructions) - 1:
        return "", None

    fn_inst = instructions[i + 1]
    if fn_inst.opcode in opc.operator_set:
        start_offset = fn_inst.offset
        if instructions[1].opname == "MAKE_FUNCTION" and opc.version_tuple >= (3, 3):
            arglist[0] = instructions[2].argval

        if fn_inst.tos_str:
            fn_name = fn_inst.tos_str
        else:
            fn_name = fn_inst.argrepr

        if opc.version_tuple >= (3, 6):
            arglist.reverse()
        s = "%s(%s)" % (fn_name, ", ".join(arglist))
        return s, start_offset
    return "", None


def extended_format_IMPORT_FROM(opc, instructions):
    assert len(instructions) >= 2
    i = 1
    while instructions[i].opname == "STORE_NAME":
        i = get_instruction_index_from_offset(
            instructions[i].start_offset, instructions, 1
        )
        if i is None:
            return "", None
    module_name = get_instruction_arg(instructions[i])
    if module_name.startswith("import_module("):
        module_name = module_name[len("import_module(") : -1]
    return (
        "from %s import %s" % (module_name, instructions[0].argval),
        instructions[-1].start_offset,
    )


def extended_format_IMPORT_NAME(opc, instructions):
    inst = instructions[0]
    return "import_module(%s)" % inst.argval, inst.offset


def extended_format_INPLACE_ADD(opc, instructions):
    return extended_format_infix_binary_op(opc, instructions, " += ")


def extended_format_INPLACE_AND(opc, instructions):
    return extended_format_infix_binary_op(opc, instructions, " &= ")


def extended_format_INPLACE_FLOOR_DIVIDE(opc, instructions):
    return extended_format_infix_binary_op(opc, instructions, " //= ")


def extended_format_INPLACE_LSHIFT(opc, instructions):
    return extended_format_infix_binary_op(opc, instructions, " <<= ")


def extended_format_INPLACE_MODULO(opc, instructions):
    return extended_format_infix_binary_op(opc, instructions, " %%= ")


def extended_format_INPLACE_MULTIPLY(opc, instructions):
    return extended_format_infix_binary_op(opc, instructions, " *= ")


def extended_format_INPLACE_OR(opc, instructions):
    return extended_format_infix_binary_op(opc, instructions, " |= ")


def extended_format_INPLACE_POWER(opc, instructions):
    return extended_format_infix_binary_op(opc, instructions, " **= ")


def extended_format_INPLACE_TRUE_DIVIDE(opc, instructions):
    return extended_format_infix_binary_op(opc, instructions, " /= ")


def extended_format_INPLACE_RSHIFT(opc, instructions):
    return extended_format_infix_binary_op(opc, instructions, " >>= ")


def extended_format_INPLACE_SUBTRACT(opc, instructions):
    return extended_format_infix_binary_op(opc, instructions, " -= ")


def extended_format_INPLACE_XOR(opc, instructions):
    return extended_format_infix_binary_op(opc, instructions, " ^= ")


def extended_format_IS_OP(opc, instructions):
    return extended_format_infix_binary_op(
        opc,
        instructions,
        "%%s %s %%s" % format_IS_OP(instructions[0].arg),
    )


def extended_format_LOAD_BUILD_CLASS(opc, instructions):
    return "class", instructions[0].start_offset


def extended_format_MAKE_FUNCTION_10_27(opc, instructions):
    """
    instructions[0] should be a "MAKE_FUNCTION" or "MAKE_CLOSURE" instruction. TOS
    should have the function or closure name.

    This code works for Python versions up to and including 2.7.
    Python docs for MAKE_FUNCTION and MAKE_CLOSURE the was changed in 33, but testing
    shows that the change was really made in Python 3.0 or so.
    """
    # From opcode description: argc indicates the total number of positional
    # and keyword arguments.  Sometimes the function name is in the stack arg
    # positions back.
    assert len(instructions) >= 2
    inst = instructions[0]
    assert inst.opname in ("MAKE_FUNCTION", "MAKE_CLOSURE")
    s = ""
    argc = instructions[0].argval
    if (argc >> 16) & 0x7FFF:
        # There is a tuple listing the parameter names for the annotations
        code_inst = instructions[2]
    else:
        code_inst = instructions[1]
    start_offset = code_inst.offset
    if code_inst.opname == "LOAD_CONST" and hasattr(code_inst.argval, "co_name"):
        # FIXME: we can probably much better than this.
        # But this is a start.
        signature = extended_function_signature(code_inst.argval)
        s += "def %s(%s): " "..." % (code_inst.argval.co_name, signature)
    return s, start_offset


def extended_format_CALL_METHOD(opc, instructions):
    """call_method should be a "CALL_METHOD" instruction. Look in
    `instructions` to see if we can find a method name.  If not we'll
    return None.

    """
    # From opcode description: arg_count indicates the total number of
    # positional and keyword arguments.

    call_method_inst = instructions[0]
    arg_count = call_method_inst.argval
    s = ""

    arglist, arg_count, first_arg = get_arglist(instructions, 0, arg_count)

    assert first_arg is not None
    if first_arg >= len(instructions) - 1:
        return "", None

    fn_inst = instructions[first_arg + 1]
    if fn_inst.opcode in opc.operator_set and arglist is not None:
        start_offset = fn_inst.offset
        if fn_inst.opname == "LOAD_METHOD":
            if fn_inst.tos_str:
                fn_name = fn_inst.tos_str
            else:
                fn_name = fn_inst.argrepr
            arglist.reverse()
            s = "%s(%s)" % (fn_name, ", ".join(arglist))
            return s, start_offset
    return "", None


def extended_format_RAISE_VARARGS_older(opc, instructions):
    raise_inst = instructions[0]
    assert raise_inst.opname == "RAISE_VARARGS"
    argc = raise_inst.argval
    start_offset = raise_inst.start_offset
    if argc == 0:
        return "reraise", start_offset
    elif argc == 1:
        exception_name_inst = instructions[1]
        start_offset = exception_name_inst.start_offset
        if exception_name_inst.tos_str:
            exception_name = exception_name_inst.tos_str
        else:
            exception_name = exception_name_inst.argrepr
        if exception_name is not None:
            return "raise %s()" % exception_name, start_offset
    return format_RAISE_VARARGS_older(raise_inst.argval), start_offset


def extended_format_RETURN_VALUE(opc, instructions):
    return extended_format_unary_op(opc, instructions, "return %s")


def extended_format_UNARY_INVERT(opc, instructions):
    return extended_format_unary_op(opc, instructions, "~(%s)")


def extended_format_UNARY_NEGATIVE(opc, instructions):
    return extended_format_unary_op(opc, instructions, "-(%s)")


def extended_format_UNARY_NOT(opc, instructions):
    return extended_format_unary_op(opc, instructions, "not (%s)")


def extended_function_signature(code):
    """
    Return some representation for a code object.
    """
    # FIXME: we can probably much better than this.
    # But this is a start.
    return "" if code.co_argcount == 0 else "..."


def get_arglist(instructions, i, arg_count):
    """
    For a variable-length instruction like BUILD_TUPLE, or
    a variable-name argument list, like CALL_FUNCTION
    accumulate and find the beginning of the list and return:
    * argument list
    * number of arguments parsed
    * the instruction index of the first instruction

    """
    arglist = []
    inst = None
    n = len(instructions) - 1
    to_do = arg_count
    while to_do > 0 and i < n:
        i += 1
        inst = instructions[i]
        if inst.is_jump_target:
            return None, -1, None

        to_do -= 1
        if inst.tos_str:
            arg = inst.tos_str
        else:
            arg = inst.argrepr
        if arg is not None:
            arglist.append(arg)
        elif not arg:
            return arglist, arg_count - to_do, i
        else:
            arglist.append("???")
        if inst.is_jump_target:
            i += 1
            break
        start_offset = inst.start_offset
        if start_offset is not None:
            j = i
            while j < len(instructions) - 1:
                j += 1
                inst2 = instructions[j]
                if inst2.offset == start_offset:
                    inst = inst2
                    if inst2.start_offset is None or inst2.start_offset == start_offset:
                        i = j
                        break
                    else:
                        start_offset = inst2.start_offset

        pass
    return arglist, arg_count - to_do, i


def get_instruction_arg(inst, argval=None):
    if argval is None:
        argval = inst.argrepr
    else:
        argval = inst.argrepr
    if inst.tos_str is not None:
        return inst.tos_str
    else:
        return argval


def get_instruction_index_from_offset(
    target_offset: int, instructions: list, start_index: int = 1
):
    for i in range(start_index, len(instructions)):
        if instructions[i].offset == target_offset:
            return i
    return None


def resolved_attrs(instructions):
>>>>>>> python-3.0-to-3.2
    """ """
    # we can probably speed up using the "tos_str" field.
    resolved = []
    start_offset = 0
    for inst in instructions:
        name = inst.argrepr
        if name:
            if name[0] == "'" and name[-1] == "'":
                name = name[1:-1]
        else:
            name = ""
        resolved.append(name)
        if inst.opname != "LOAD_ATTR":
            start_offset = inst.offset
            break
    return ".".join(reversed(resolved)), start_offset


def safe_repr(obj, max_len=20):
    """
    String repr with length at most ``max_len``
    """
    try:
        result = repr(obj)
    except Exception:
        result = object.__repr__(obj)
    if len(result) > max_len:
        return result[:max_len] + "..."
    return result


def short_code_repr(code):
    """
    A shortened string representation of a code object
    """
    if hasattr(code, "co_name"):
        return "<code object %s>" % code.co_name
    else:
        return "<code object %s>" % code


def skip_cache(instructions, i):
    """Python 3.11+ has CACHE instructions.
    Skip over those starting at index i and return
    the index of the first instruction that is not CACHE
    or return the length of the list if we can't find
    such an instruction.
    """
    n = len(instructions)
    while i < n and instructions[i].opname == "CACHE":
        i += 1
    return i


# fmt: off
# The below are roughly Python 3.3 based. Python 3.11 removes some of these.
opcode_extended_fmt_base = {
    "BINARY_ADD":            extended_format_BINARY_ADD,
    "BINARY_AND":            extended_format_BINARY_AND,
    "BINARY_FLOOR_DIVIDE":   extended_format_BINARY_FLOOR_DIVIDE,
    "BINARY_MODULO":         extended_format_BINARY_MODULO,
    "BINARY_MULTIPLY":       extended_format_BINARY_MULTIPLY,
    "BINARY_RSHIFT":         extended_format_BINARY_RSHIFT,
    "BINARY_SUBSCR":         extended_format_BINARY_SUBSCR,
    "BINARY_SUBTRACT":       extended_format_BINARY_SUBTRACT,
    "BINARY_TRUE_DIVIDE":    extended_format_BINARY_TRUE_DIVIDE,
    "BINARY_LSHIFT":         extended_format_BINARY_LSHIFT,
    "BINARY_OR":             extended_format_BINARY_OR,
    "BINARY_POWER":          extended_format_BINARY_POWER,
    "BINARY_XOR":            extended_format_BINARY_XOR,
    "BUILD_CONST_KEY_MAP":   extended_format_BUILD_CONST_KEY_MAP,
    "BUILD_LIST":            extended_format_BUILD_LIST,
    "BUILD_SET":             extended_format_BUILD_SET,
    "BUILD_SLICE":           extended_format_BUILD_SLICE,
    "BUILD_TUPLE":           extended_format_BUILD_TUPLE,
    "CALL_FUNCTION":         extended_format_CALL_FUNCTION,
    "COMPARE_OP":            extended_format_COMPARE_OP,
    "IMPORT_FROM":           extended_format_IMPORT_FROM,
    "IMPORT_NAME":           extended_format_IMPORT_NAME,
    "INPLACE_ADD":           extended_format_INPLACE_ADD,
    "INPLACE_AND":           extended_format_INPLACE_AND,
    "INPLACE_FLOOR_DIVIDE":  extended_format_INPLACE_FLOOR_DIVIDE,
    "INPLACE_LSHIFT":        extended_format_INPLACE_LSHIFT,
    "INPLACE_MODULO":        extended_format_INPLACE_MODULO,
    "INPLACE_MULTIPLY":      extended_format_INPLACE_MULTIPLY,
    "INPLACE_OR":            extended_format_INPLACE_OR,
    "INPLACE_POWER":         extended_format_INPLACE_POWER,
    "INPLACE_RSHIFT":        extended_format_INPLACE_RSHIFT,
    "INPLACE_SUBTRACT":      extended_format_INPLACE_SUBTRACT,
    "INPLACE_TRUE_DIVIDE":   extended_format_INPLACE_TRUE_DIVIDE,
    "INPLACE_XOR":           extended_format_INPLACE_XOR,
    "IS_OP":                 extended_format_IS_OP,
    "LOAD_ATTR":             extended_format_ATTR,
    "LOAD_BUILD_CLASS":      extended_format_LOAD_BUILD_CLASS,
    "MAKE_FUNCTION":         extended_format_MAKE_FUNCTION_10_27,
    "RAISE_VARARGS":         extended_format_RAISE_VARARGS_older,
    "RETURN_VALUE":          extended_format_RETURN_VALUE,
    "STORE_ATTR":            extended_format_ATTR,
    "STORE_DEREF":           extended_format_store_op,
    "STORE_FAST":            extended_format_store_op,
    "STORE_GLOBAL":          extended_format_store_op,
    "STORE_NAME":            extended_format_store_op,
    "STORE_SUBSCR":          extended_format_STORE_SUBSCR,
    "UNARY_INVERT":          extended_format_UNARY_INVERT,
    "UNARY_NEGATIVE":        extended_format_UNARY_NEGATIVE,
    "UNARY_NOT":             extended_format_UNARY_NOT,
}
# fmt: on
