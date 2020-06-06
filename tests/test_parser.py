from textwrap import dedent

import pytest

from translator.parser import (
    clean_instructions,
    ByteCodeInst,
    Command,
    Segment,
    InvalidSegmentException,
)


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
        ("\n\n\tpush temp 9 // add to stack", "push temp 9"),
    ],
)
def test_clean_instructions(ins, expected):
    cleaned = clean_instructions(ins, to_lower=True)
    assert cleaned == expected


@pytest.mark.parametrize(
    "inst, byte_code",
    [
        ("add", ByteCodeInst(label_suffix="", cmd=Command.ADD)),
        (
            "push constant 5",
            ByteCodeInst(
                label_suffix="", cmd=Command.PUSH, segment=Segment.CONSTANT, value=5
            ),
        ),
        (
            "push constant 6",
            ByteCodeInst(
                label_suffix="", cmd=Command.PUSH, segment=Segment.CONSTANT, value=6
            ),
        ),
    ],
)
def test_inst_to_byte_code(inst: str, byte_code: ByteCodeInst) -> None:
    assert ByteCodeInst.from_string(inst, label_suffix="") == byte_code


@pytest.mark.parametrize(
    "byte_code, asm",
    [
        (
            ByteCodeInst.from_string("push constant 6"),
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
            ByteCodeInst.from_string("push argument 6"),
            "@6\nD=A\n@ARG\nD=D+M\nA=D\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1",
        ),
        (
            ByteCodeInst.from_string("push local 6"),
            "@6\nD=A\n@LCL\nD=D+M\nA=D\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1",
        ),
        (
            ByteCodeInst.from_string("push this 6"),
            "@6\nD=A\n@THIS\nD=D+M\nA=D\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1",
        ),
        (
            ByteCodeInst.from_string("push that 6"),
            "@6\nD=A\n@THAT\nD=D+M\nA=D\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1",
        ),
    ],
)
def test_push_arg_to_asm(byte_code, asm):
    assert byte_code.to_asm() == asm


@pytest.mark.parametrize(
    "byte_code, asm",
    [
        (
            ByteCodeInst.from_string("add"),
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
            ByteCodeInst.from_string("sub"),
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
            ByteCodeInst.from_string("eq", label_suffix=""),
            "@SP\nM=M-1\nA=M\nD=M\n@SP\nM=M-1\nA=M\nD=M-D\nM=D\n"
            "@IS_EQ\nD;JEQ\n@ELSE\nD;JNE\n(IS_EQ)\n@SP\nA=M\nM=-1\n@SP\nM=M+1\n"
            "@END_IF\n0;JEQ\n(ELSE)\n@SP\nA=M\nM=0\n@SP\nM=M+1\n(END_IF)\nD=0",
        )
    ],
)
def test_eq_to_asm(byte_code, asm):
    assert byte_code.to_asm() == asm


@pytest.mark.parametrize(
    "byte_code, asm",
    [
        (
            ByteCodeInst.from_string("lt", label_suffix=""),
            "@SP\nM=M-1\nA=M\nD=M\n@SP\nM=M-1\nA=M\nD=M-D\nM=D\n"
            "@IS_LESS_THAN\nD;JLT\n@ELSE\nD;JGE\n(IS_LESS_THAN)\n"
            "@SP\nA=M\nM=-1\n@SP\nM=M+1\n@END_IF\n0;JEQ\n(ELSE)\n"
            "@SP\nA=M\nM=0\n@SP\nM=M+1\n(END_IF)\nD=0",
        )
    ],
)
def test_lt_to_asm(byte_code, asm):
    assert byte_code.to_asm() == asm


@pytest.mark.parametrize(
    "byte_code, asm",
    [
        (
            ByteCodeInst.from_string("gt", label_suffix=""),
            "@SP\nM=M-1\nA=M\nD=M\n@SP\nM=M-1\nA=M\nD=M-D\nM=D\n@IS_GT\nD;JGT\n"
            "@ELSE\nD;JLE\n(IS_GT)\n@SP\nA=M\nM=-1\n@SP\nM=M+1\n@END_IF\n0;JEQ\n"
            "(ELSE)\n@SP\nA=M\nM=0\n@SP\nM=M+1\n(END_IF)\nD=0",
        )
    ],
)
def test_lt_to_asm(byte_code, asm):
    assert byte_code.to_asm() == asm


@pytest.mark.parametrize(
    "byte_code, asm",
    [
        (
            ByteCodeInst.from_string(line="not"),
            "@SP\nM=M-1\nA=M\nD=M\n@SP\nA=M\nM=!D\n@SP\nM=M+1",
        )
    ],
)
def test_not_to_asm(byte_code, asm):
    assert byte_code.to_asm() == asm


@pytest.mark.parametrize(
    "byte_code, asm",
    [
        (
            ByteCodeInst.from_string(line="neg"),
            "@SP\nM=M-1\nA=M\nD=M\n@SP\nA=M\nM=-D\n@SP\nM=M+1",
        )
    ],
)
def test_not_to_asm(byte_code, asm):
    assert byte_code.to_asm() == asm


@pytest.mark.parametrize(
    "byte_code, asm",
    [
        (
            ByteCodeInst.from_string(line="and"),
            "@SP\nM=M-1\nA=M\nD=M\n@SP\nM=M-1\nA=M\nM=M&D\n@SP\nM=M+1",
        )
    ],
)
def test_and_to_asm(byte_code, asm):
    assert byte_code.to_asm() == asm


@pytest.mark.parametrize(
    "byte_code, asm",
    [
        (
            ByteCodeInst.from_string(line="or"),
            "@SP\nM=M-1\nA=M\nD=M\n@SP\nM=M-1\nA=M\nM=M|D\n@SP\nM=M+1",
        )
    ],
)
def test_or_to_asm(byte_code, asm):
    assert byte_code.to_asm() == asm


@pytest.mark.parametrize(
    "byte_code, asm",
    [
        (
            ByteCodeInst.from_string(line="push argument 7"),
            "@7\nD=A\n@ARG\nD=D+M\nA=D\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1",
        ),
        (
            ByteCodeInst.from_string(line="pop argument 7"),
            "@7\nD=A\n@ARG\nD=D+M\n@SP\nM=M-1\nA=M\nD=D+M\nA=D-M\nM=D-A",
        ),
        (
            ByteCodeInst.from_string(line="push local 7"),
            "@7\nD=A\n@LCL\nD=D+M\nA=D\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1",
        ),
        (
            ByteCodeInst.from_string(line="pop local 7"),
            "@7\nD=A\n@LCL\nD=D+M\n@SP\nM=M-1\nA=M\nD=D+M\nA=D-M\nM=D-A",
        ),
        (
            ByteCodeInst.from_string(line="push this 7"),
            "@7\nD=A\n@THIS\nD=D+M\nA=D\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1",
        ),
        (
            ByteCodeInst.from_string(line="pop this 7"),
            "@7\nD=A\n@THIS\nD=D+M\n@SP\nM=M-1\nA=M\nD=D+M\nA=D-M\nM=D-A",
        ),
        (
            ByteCodeInst.from_string(line="push that 7"),
            "@7\nD=A\n@THAT\nD=D+M\nA=D\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1",
        ),
        (
            ByteCodeInst.from_string(line="pop that 7"),
            "@7\nD=A\n@THAT\nD=D+M\n@SP\nM=M-1\nA=M\nD=D+M\nA=D-M\nM=D-A",
        ),
    ],
)
def test_segments_to_asm(byte_code, asm):
    """Tests generic segments: LCL, ARG, THIS, THAT"""
    assert byte_code.to_asm() == asm


@pytest.mark.parametrize(
    "byte_code, asm",
    [
        (
            ByteCodeInst.from_string(line="push temp 7"),
            "@7\nD=A\n@5\nD=D+A\nA=D\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1",
        ),
        (
            ByteCodeInst.from_string(line="pop temp 6"),
            "@6\nD=A\n@5\nD=D+A\n@SP\nM=M-1\nA=M\nD=D+M\nA=D-M\nM=D-A",
        ),
    ],
)
def test_temp_to_asm(byte_code, asm):
    assert byte_code.to_asm() == asm


@pytest.mark.parametrize(
    "byte_code, asm",
    [
        (
            ByteCodeInst.from_string(line="push static 7", static_label="Test"),
            "@Test.7\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1",
        ),
        (
            ByteCodeInst.from_string(line="pop static 6", static_label="Test"),
            "@SP\nM=M-1\nA=M\nD=M\n@Test.6\nM=D",
        ),
    ],
)
def test_static_to_asm(byte_code, asm):
    assert byte_code.to_asm() == asm


@pytest.mark.parametrize(
    "byte_code, asm",
    [
        (
            ByteCodeInst.from_string(line="push pointer 0"),
            "@THIS\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1",
        ),
        (
            ByteCodeInst.from_string(line="push pointer 1"),
            "@THAT\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1",
        ),
        (
            ByteCodeInst.from_string(line="pop pointer 0"),
            "@SP\nM=M-1\nA=M\nD=M\n@THIS\nM=D",
        ),
        (
            ByteCodeInst.from_string(line="pop pointer 1"),
            "@SP\nM=M-1\nA=M\nD=M\n@THAT\nM=D",
        ),
    ],
)
def test_pointer_to_asm(byte_code, asm):
    assert byte_code.to_asm() == asm


@pytest.mark.parametrize(
    "byte_code",
    [
        ByteCodeInst.from_string(line="push pointer -1"),
        ByteCodeInst.from_string(line="push pointer 2"),
        ByteCodeInst.from_string(line="push pointer 32"),
        ByteCodeInst.from_string(line="push pointer 022"),
    ],
)
def test_pointer_must_be_0_or_1(byte_code):
    with pytest.raises(InvalidSegmentException):
        byte_code.to_asm()
