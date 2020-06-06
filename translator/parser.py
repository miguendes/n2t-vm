import random
import re
from dataclasses import dataclass
from enum import Enum, auto
from textwrap import dedent
from typing import List, Optional

COMMENT_TOKEN = "//"


def clean(ins: str) -> List[str]:
    for line in ins.split("\n"):
        line = line.strip()
        if COMMENT_TOKEN in line:
            line = line[: line.index(COMMENT_TOKEN)].strip()
        if not line:
            continue
        line = " ".join(re.split(r"\s+", line, flags=re.UNICODE))
        yield line


def clean_instructions(ins: str, to_lower: bool = False) -> str:
    inst = "\n".join(clean(ins))
    return inst.lower() if to_lower else inst


class InvalidCommandException(Exception):
    """Raised when a command is built from a non-existent command."""


class InvalidSegmentException(Exception):
    """Raised when a command is built from a non-existent command."""


class Command(Enum):
    PUSH = 1
    POP = 2
    ADD = 3
    SUB = 4
    NEG = 5
    EQ = 6
    GT = 7
    LT = 8
    AND = 9
    OR = 10
    NOT = 11

    @classmethod
    def from_string(cls, raw_cmd: str) -> "Command":
        str_to_cmd = {
            "push": cls.PUSH,
            "pop": cls.POP,
            "add": cls.ADD,
            "sub": cls.SUB,
            "neg": cls.NEG,
            "eq": cls.EQ,
            "lt": cls.LT,
            "gt": cls.GT,
            "not": cls.NOT,
            "and": cls.AND,
            "or": cls.OR,
        }
        try:
            return str_to_cmd[raw_cmd]
        except KeyError as e:
            raise InvalidCommandException("Invalid command.") from e


class Segment(Enum):
    CONSTANT = auto()
    LCL = auto()
    ARG = auto()
    THIS = auto()
    THAT = auto()
    TEMP = auto()

    @classmethod
    def from_string(cls, raw_seg: str) -> "Segment":
        str_to_seg = {
            "constant": cls.CONSTANT,
            "argument": cls.ARG,
            "local": cls.LCL,
            "this": cls.THIS,
            "that": cls.THAT,
            "temp": cls.TEMP,
        }
        try:
            return str_to_seg[raw_seg]
        except KeyError as e:
            raise InvalidSegmentException("Invalid segment.") from e

    def __str__(self) -> str:
        return str(self.name).upper()


@dataclass
class ByteCodeInst:
    label_suffix: str
    cmd: Command
    segment: Optional[Segment] = None
    value: Optional[int] = None

    @classmethod
    def from_string(
        cls, line: str, label_suffix: Optional[str] = None
    ) -> "ByteCodeInst":
        if label_suffix is None:
            label_suffix = str(random.randint(0, 1_000_000))

        tokens = line.split()

        try:
            raw_cmd, raw_seg, value = tokens
        except ValueError:
            return cls(label_suffix, Command.from_string(tokens[0]))

        return cls(
            label_suffix,
            Command.from_string(raw_cmd),
            Segment.from_string(raw_seg),
            int(value),
        )

    def to_asm(self) -> str:
        """
        Returns a clean set of assembly instructions that performs
        the byte code operation.
        """
        if self.cmd == Command.PUSH and self.segment == Segment.CONSTANT:
            inst = self._build_push_constant()
        elif self.segment == Segment.TEMP:
            inst = self._handle_temp()
        elif self.cmd == Command.PUSH:
            inst = self._build_push_segment()
        elif self.cmd == Command.POP:
            inst = self._build_pop_segment()
        elif self.cmd == Command.ADD:
            inst = self._build_add()
        elif self.cmd == Command.SUB:
            inst = self._build_sub()
        elif self.cmd == Command.EQ:
            inst = self._build_eq()
        elif self.cmd == Command.LT:
            inst = self._build_lt()
        elif self.cmd == Command.GT:
            inst = self._build_gt()
        elif self.cmd == Command.NOT:
            inst = self._build_not()
        elif self.cmd == Command.NEG:
            inst = self._build_neg()
        elif self.cmd == Command.AND:
            inst = self._build_and()
        elif self.cmd == Command.OR:
            inst = self._build_or()
        else:
            raise ValueError("Unsupported command.")

        return clean_instructions(inst)

    def _handle_temp(self):
        if self.cmd == Command.PUSH:
            inst = self._build_push_temp()
        else:
            inst = self._build_pop_temp()
        return inst

    def _build_push_constant(self) -> str:
        """
        *SP = value
        SP++
        """
        value = self.value
        return dedent(
            f"""
            @{value}
            D=A
            @SP
            A=M
            M=D
            @SP
            M=M+1
            """
        )

    def _build_add(self) -> str:
        """
        SP--
        temp0 = *SP
        SP--
        *SP = *SP - temp0
        SP++
        """
        return dedent(
            """
            @SP
            M=M-1
            A=M
            D=M
            @SP
            M=M-1
            A=M
            M=M+D
            @SP
            M=M+1
            """
        )

    def _build_sub(self) -> str:
        """
        SP--
        temp0 = *SP
        SP--
        *SP = *SP - temp0
        SP++
        """
        return dedent(
            """
            @SP
            M=M-1
            A=M
            D=M
            @SP
            M=M-1
            A=M
            M=M-D
            @SP
            M=M+1
            """
        )

    def _build_eq(self) -> str:
        """
        eq -> x==0


        SP--
        temp0 = *SP
        SP--
        *SP = 0 == temp0
        SP++
        """
        return dedent(
            f"""
            // SP--
            @SP
            M=M-1
            // D = *SP
            A=M
            D=M
            // SP--
            @SP
            M=M-1
            // D = *SP - D  <--> x - y
            A=M
            D=M-D
            M=D
    
            // if x == 0
            @IS_EQ{self.label_suffix}
            D;JEQ
            // else
            @ELSE{self.label_suffix}
            D;JNE
    
            (IS_EQ{self.label_suffix})
            // True in Hack ASM is -1
            @SP
            A=M
            M=-1
            // SP++
            @SP
            M=M+1
            @END_IF{self.label_suffix}
            0;JEQ
    
            (ELSE{self.label_suffix})
            // False in Hack ASM is 0
            @SP
            A=M
            M=0
            // SP++
            @SP
            M=M+1
    
            (END_IF{self.label_suffix})
            D=0
            """
        )

    def _build_lt(self) -> str:
        """
        lt -> x < y

        SP--
        x = *SP
        SP--
        y = *SP
        *SP = -1 if x < y else 0
        SP++
        """
        return dedent(
            f"""
            // SP--
            @SP
            M=M-1
            // D = *SP
            A=M
            D=M
            // SP--
            @SP
            M=M-1
            // D = *SP - D  <--> x - y
            A=M
            D=M-D
            M=D

            // if x < 0
            @IS_LESS_THAN{self.label_suffix}
            D;JLT
            // else
            @ELSE{self.label_suffix}
            D;JGE

            (IS_LESS_THAN{self.label_suffix})
            // True in Hack ASM is -1
            @SP
            A=M
            M=-1
            // SP++
            @SP
            M=M+1
            @END_IF{self.label_suffix}
            0;JEQ

            (ELSE{self.label_suffix})
            // False in Hack ASM is 0
            @SP
            A=M
            M=0
            // SP++
            @SP
            M=M+1
            
            (END_IF{self.label_suffix})
            D=0
            """
        )

    def _build_gt(self) -> str:
        """
        lt -> x > y

        SP--
        x = *SP
        SP--
        y = *SP
        *SP = -1 if x > y else 0
        SP++
        """
        return dedent(
            f"""
            // SP--
            @SP
            M=M-1
            // D = *SP
            A=M
            D=M
            // SP--
            @SP
            M=M-1
            // D = *SP - D  <--> x - y
            A=M
            D=M-D
            M=D

            // if x > 0
            @IS_GT{self.label_suffix}
            D;JGT
            // else
            @ELSE{self.label_suffix}
            D;JLE

            (IS_GT{self.label_suffix})
            // True in Hack ASM is -1
            @SP
            A=M
            M=-1
            // SP++
            @SP
            M=M+1
            @END_IF{self.label_suffix}
            0;JEQ

            (ELSE{self.label_suffix})
            // False in Hack ASM is 0
            @SP
            A=M
            M=0
            // SP++
            @SP
            M=M+1

            (END_IF{self.label_suffix})
            D=0
            """
        )

    def _build_not(self):
        """
         not -> !x

         SP--
         x = *SP
         *SP = !*SP
         SP++
         """
        return dedent(
            f"""
            // SP--
            @SP
            M=M-1
            // D = *SP
            A=M
            D=M
            // *SP = !D
            @SP
            A=M
            M=!D
            @SP
            M=M+1
            """
        )

    def _build_neg(self):
        """
         neg -> -x

         SP--
         x = *SP
         *SP = 0 - *SP
         SP++
         """
        return dedent(
            f"""
            // SP--
            @SP
            M=M-1
            // D = *SP
            A=M
            D=M
            // *SP = 0 - D
            @SP
            A=M
            M=-D
            @SP
            M=M+1
            """
        )

    def _build_and(self) -> str:
        """
        SP--
        temp0 = *SP
        SP--
        *SP = *SP & temp0
        SP++
        """
        return dedent(
            """
            @SP
            M=M-1
            A=M
            D=M
            @SP
            M=M-1
            A=M
            M=M&D
            @SP
            M=M+1
            """
        )

    def _build_or(self) -> str:
        """
        SP--
        temp0 = *SP
        SP--
        *SP = *SP | temp0
        SP++
        """
        return dedent(
            """
            @SP
            M=M-1
            A=M
            D=M
            @SP
            M=M-1
            A=M
            M=M|D
            @SP
            M=M+1
            """
        )

    def _build_push_segment(self):
        """
        addr = ARG + value
        *SP = *addr
        SP++
        """
        value = self.value
        label = str(self.segment)
        return dedent(
            f"""
            // D = offset
            @{value}
            D=A
            // D = D + ARG
            @{label}
            D=D+M
            // *SP = *D
            A=D
            D=M
            @SP
            A=M
            M=D
            // SP++
            @SP
            M=M+1
            """
        )

    def _build_pop_segment(self):
        """
        addr = segmentPointer + offset
        SP--
        *addr = *SP
        """
        value = self.value
        label = str(self.segment)
        return dedent(
            f"""
            // D = offset
            @{value}
            D=A
            // D = offset + segmentPointer
            @{label}
            D=D+M
            // SP--
            @SP
            M=M-1
            A=M
            D=D+M  // addr = addr + RAM[SP]
            A=D-M  // A = addr - RAM[SP] 
            M=D-A  // RAM[A] = addr - A
            """
        )

    def _build_push_temp(self):
        """
        addr = ARG + value
        *SP = *addr
        SP++
        """
        value = self.value
        return dedent(
            f"""
              // i = offset
              @{value}
              D=A
              // addr = i + 5
              @5
              D=D+A
              // *SP = *addr
              A=D
              D=M
              @SP
              A=M
              M=D
              // SP++
              @SP
              M=M+1
              """
        )

    def _build_pop_temp(self):
        """
        addr = ARG + value
        SP--
        *addr = *SP
        """
        value = self.value
        return dedent(
            f"""
              @{value}
              D=A // D = i
              @5
              D=D+A // addr = 5 + i
              @SP
              M=M-1
              A=M
              D=D+M  // addr = addr + RAM[SP]
              A=D-M  // A = addr - RAM[SP] 
              M=D-A  // RAM[A] = addr - A
              """
        )


def parse(ins: str) -> List[ByteCodeInst]:
    for line in ins.split("\n"):
        yield ByteCodeInst.from_string(line)
