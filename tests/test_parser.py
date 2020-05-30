from textwrap import dedent

import pytest

from translator.parser import clean_instructions, ByteCodeInst, Command, Segment


@pytest.mark.parametrize(
    "ins, expected",
    [
        (
            dedent(
                """
        push constant    8
        
        pop temp 7
        
        add
        
        
            
        """.upper()
            ),
            """push constant 8\npop temp 7\nadd""",
        ),
        ("\n\n\n", ""),
        ("\n\n\tpush temp 9\n\n\n\n\n\t", "push temp 9"),
        (
            dedent(
                """//this is a comment
             push temp 9
             // push temp 9
             """
            ),
            "push temp 9",
        ),
    ],
)
def test_clean_instructions(ins, expected):
    cleaned = clean_instructions(ins)
    assert cleaned == expected


@pytest.mark.parametrize(
    "inst, byte_code",
    [
        ("add", ByteCodeInst(cmd=Command.ADD)),
        (
            "push constant 5",
            ByteCodeInst(cmd=Command.PUSH, segment=Segment.CONSTANT, value=5),
        ),
        (
            "push constant 6",
            ByteCodeInst(cmd=Command.PUSH, segment=Segment.CONSTANT, value=6),
        ),
    ],
)
def test_inst_to_byte_code(inst: str, byte_code: ByteCodeInst) -> None:
    assert ByteCodeInst.from_string(inst) == byte_code


@pytest.mark.parametrize(
    "byte_code, asm",
    [
        (
            ByteCodeInst(cmd=Command.PUSH, segment=Segment.CONSTANT, value=6),
            clean_instructions(
                dedent(
                    """
                @6
                D=A
                @SP
                A=M
                M=D
                // Comment
                @SP
                M=M+1   
                """
                )
            ),
        )
    ],
)
def test_push_const_to_asm(byte_code, asm):
    assert byte_code.to_assembly() == asm


@pytest.mark.parametrize(
    "byte_code, asm",
    [
        (
            ByteCodeInst(cmd=Command.ADD),
            clean_instructions(
                dedent(
                    """
                @SP
                M=M-1
                A=M
                D=M
                @SP
                M=M-1
                A=M
                M=D+M
                @SP
                M=M+1
                """
                )
            ),
        )
    ],
)
def test_add_to_asm(byte_code, asm):
    assert byte_code.to_assembly() == (asm)
