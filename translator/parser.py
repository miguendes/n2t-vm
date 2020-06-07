import random
import re
from dataclasses import dataclass
from enum import Enum, auto
from textwrap import dedent
from typing import List, Optional

NEW_LINE_TOKEN = "\n"

COMMENT_TOKEN = "//"


def clean(ins: str) -> List[str]:
    for line in ins.split(NEW_LINE_TOKEN):
        line = line.strip()
        if COMMENT_TOKEN in line:
            line = line[: line.index(COMMENT_TOKEN)].strip()
        if not line:
            continue
        line = " ".join(re.split(r"\s+", line, flags=re.UNICODE))
        yield line


def clean_instructions(ins: str, to_lower: bool = False) -> str:
    inst = NEW_LINE_TOKEN.join(clean(ins))
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
    STATIC = auto()
    POINTER = auto()

    @classmethod
    def from_string(cls, raw_seg: str) -> "Segment":
        str_to_seg = {
            "constant": cls.CONSTANT,
            "argument": cls.ARG,
            "local": cls.LCL,
            "this": cls.THIS,
            "that": cls.THAT,
            "temp": cls.TEMP,
            "static": cls.STATIC,
            "pointer": cls.POINTER,
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
    static_label: Optional[str] = None

    @classmethod
    def from_string(
        cls,
        line: str,
        label_suffix: Optional[str] = None,
        static_label: Optional[str] = None,
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
            static_label,
        )

    def to_asm(self) -> str:
        """
        Returns a clean set of assembly instructions that performs
        the byte code operation.
        """
        try:
            build_instruction = self._handlers_map()[self.segment]
            return clean_instructions(build_instruction())
        except KeyError:
            pass
        try:
            build_instruction = self._handlers_map()[self.cmd]
            return clean_instructions(build_instruction())
        except KeyError:
            raise ValueError("Unsupported command.")

    def _handlers_map(self):
        """Maps segments and commands to a handler."""
        return {
            Segment.CONSTANT: self._build_push_constant,
            Segment.TEMP: self._handle_temp,
            Segment.STATIC: self._handle_static,
            Segment.POINTER: self._handle_pointer,
            Segment.LCL: self._handle_generic_segment,
            Segment.ARG: self._handle_generic_segment,
            Segment.THIS: self._handle_generic_segment,
            Segment.THAT: self._handle_generic_segment,
            Command.ADD: self._build_add,
            Command.SUB: self._build_sub,
            Command.EQ: self._build_eq,
            Command.GT: self._build_gt,
            Command.NOT: self._build_not,
            Command.NEG: self._build_neg,
            Command.AND: self._build_and,
            Command.OR: self._build_or,
        }

    def _handle_temp(self):
        """Handle push/pop temp case."""
        if self.cmd == Command.PUSH:
            inst = self._build_push_temp()
        else:
            inst = self._build_pop_temp()
        return inst

    def _handle_static(self):
        """Handle push/pop static case."""
        if self.cmd == Command.PUSH:
            inst = self._build_push_static()
        else:
            inst = self._build_pop_static()
        return inst

    def _handle_pointer(self):
        """Handle push/pop pointer case."""
        if self.cmd == Command.PUSH:
            inst = self._build_push_pointer()
        else:
            inst = self._build_pop_pointer()
        return inst

    def _handle_generic_segment(self):
        """Push/Pop to/from LCL, ARG, THIS, THAT"""
        if self.cmd == Command.PUSH:
            inst = self._build_push_segment()
        else:
            inst = self._build_pop_segment()
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

    def _build_push_static(self):
        """
        *SP = *static
        SP++
        """
        value = self.value
        static_label = self.static_label
        return dedent(
            f"""
              @{static_label}.{value}
              D=M
              @SP
              A=M
              M=D
              // SP++
              @SP
              M=M+1
              """
        )

    def _build_pop_static(self):
        """
        SP--
        *static = *SP
        """
        value = self.value
        static_label = self.static_label
        return dedent(
            f"""
              // SP--
              @SP
              M=M-1
              // temp = *SP
              A=M
              D=M
              // *static = temp
              @{static_label}.{value}
              M=D
              """
        )

    def _get_pointer(self) -> str:
        """Returns the appropriate label for the pointer"""
        pointers = {1: "THAT", 0: "THIS"}
        try:
            return pointers[self.value]
        except KeyError:
            raise InvalidSegmentException(
                f"Expected pointer be 0 or 1 but got {self.value}"
            )

    def _build_push_pointer(self):
        """
        *SP = THIS/THAT
        SP++
        """
        return dedent(
            f"""
              // temp = THIS
              @{self._get_pointer()}
              D=M
              // *SP = temp
              @SP
              A=M
              M=D
              // SP++
              @SP
              M=M+1
              """
        )

    def _build_pop_pointer(self):
        """
        *SP = THIS/THAT
        SP++
        """
        return dedent(
            f"""
              // SP--
              @SP
              M=M-1
              // temp = *SP
              A=M
              D=M
              // pointer = temp
              @{self._get_pointer()}
              M=D
              """
        )


def parse(ins: str, filename: str) -> List[ByteCodeInst]:
    """
    Parses a instruction a set of bytecode instructions as string
    to a list of ByteCodeInst.
    """
    for line in ins.split(NEW_LINE_TOKEN):
        yield ByteCodeInst.from_string(line, static_label=filename)
