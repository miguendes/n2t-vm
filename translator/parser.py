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
        yield line.lower()


def clean_instructions(ins: str) -> str:
    return "\n".join(clean(ins))


class Command(Enum):
    PUSH = 1
    POP = 2
    ADD = 3


class Segment(Enum):
    CONSTANT = 1


@dataclass
class ByteCodeInst:
    _SYMBOL_TABLE = {
        "push": Command.PUSH,
        "pop": Command.POP,
        "add": Command.ADD,
        "constant": Segment.CONSTANT,
    }

    cmd: Command
    segment: Optional[Segment] = None
    value: Optional[int] = None

    @classmethod
    def from_string(cls, line: str) -> "ByteCodeInst":
        tokens = line.split()
        try:
            raw_cmd, raw_seg, value = tokens
            cmd = cls._SYMBOL_TABLE[raw_cmd]
            segment = cls._SYMBOL_TABLE[raw_seg]
            value = int(value)
            return cls(cmd, segment, value)
        except ValueError:
            cmd = cls._SYMBOL_TABLE[tokens[0]]
            return cls(cmd)

    def to_assembly(self) -> str:
        if self.cmd == Command.PUSH and self.segment.CONSTANT:
            inst = self._build_push_constant()
        elif self.cmd == Command.ADD:
            inst = self._build_add()
        else:
            inst = ""

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
        *SP = temp0 + *SP
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
            M=D+M
            @SP
            M=M+1     
            """
        )


def parse(ins: str) -> List[ByteCodeInst]:
    for line in ins.split("\n"):
        yield ByteCodeInst.from_string(line)
