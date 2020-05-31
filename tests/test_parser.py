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
    cleaned = clean_instructions(ins, to_lower=True)
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
            "@6\nD=A\n@SP\nA=M\nM=D\n@SP\nM=M+1",
        )
    ],
)
def test_push_const_to_asm(byte_code, asm):
    assert byte_code.to_asm() == asm


@pytest.mark.parametrize(
    "byte_code, asm",
    [
        (
            ByteCodeInst(cmd=Command.ADD),
            "@SP\nM=M-1\nA=M\nD=M\n@SP\nM=M-1\nA=M\nM=M-D\n@SP\nM=M+1",
        )
    ],
)
def test_add_to_asm(byte_code, asm):
    assert byte_code.to_asm() == asm


@pytest.mark.parametrize(
    "byte_code, asm",
    [
        (
            ByteCodeInst(cmd=Command.SUB),
            "@SP\nM=M-1\nA=M\nD=M\n@SP\nM=M-1\nA=M\nM=M-D\n@SP\nM=M+1",
        )
    ],
)
def test_add_to_asm(byte_code, asm):
    assert byte_code.to_asm() == asm


@pytest.mark.parametrize(
    "byte_code, asm",
    [
        (
            ByteCodeInst(cmd=Command.EQ),
            "@SP\nM=M-1\nA=M\nD=M\n@SP\nM=M-1\nA=M\nM=!M\nD=D&M\n"
            "@EQUAL\nD;JEQ\n@NOT_EQUAL\nD;JNE\n"
            "(EQUAL)\n@SP\nA=M\nM=-1\n@SP\nM=M+1\n"
            "(NOT_EQUAL)\n@SP\nA=M\nM=0\n@SP\nM=M+1",
        )
    ],
)
def test_eq_to_asm(byte_code, asm):
    assert byte_code.to_asm() == asm
