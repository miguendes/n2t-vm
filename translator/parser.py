import random
import re
from dataclasses import dataclass
from enum import Enum
from textwrap import dedent
from typing import List, Optional


def clean(ins: str) -> List[str]:
    for line in ins.split("\n"):
        line = line.strip()
        if not line or line.startswith("//"):
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
        if raw_cmd == "push":
            return cls.PUSH
        elif raw_cmd == "pop":
            return cls.POP
        elif raw_cmd == "add":
            return cls.ADD
        elif raw_cmd == "sub":
            return cls.SUB
        elif raw_cmd == "neg":
            return cls.NEG
        elif raw_cmd == "eq":
            return cls.EQ
        elif raw_cmd == "lt":
            return cls.LT
        elif raw_cmd == "gt":
            return cls.GT
        elif raw_cmd == "not":
            return cls.NOT
        else:
            raise InvalidCommandException("Invalid command.")


class Segment(Enum):
    CONSTANT = 1

    _SYMBOL_TABLE = {"constant": CONSTANT}

    @classmethod
    def from_string(cls, raw_seg: str) -> "Segment":
        if raw_seg == "constant":
            return cls.CONSTANT
        else:
            raise InvalidSegmentException("Invalid segment.")


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
        if self.cmd == Command.PUSH and self.segment.CONSTANT:
            inst = self._build_push_constant()
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
        else:
            raise ValueError("Unsupported command.")

        return clean_instructions(inst)

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


def parse(ins: str) -> List[ByteCodeInst]:
    for line in ins.split("\n"):
        yield ByteCodeInst.from_string(line)
