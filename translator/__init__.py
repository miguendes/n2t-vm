import pathlib

from translator.parser import parse, clean_instructions

SIMPLE_ADD_DIR = pathlib.Path("/home/miguel/nand2tetris/projects/07/StackArithmetic/SimpleAdd")

SIMPLE_ADD = SIMPLE_ADD_DIR / "SimpleAdd.vm"
SIMPLE_ADD_ASM = SIMPLE_ADD_DIR / "SimpleAdd.asm"

def translate(inst: str) -> str:
    cleaned_inst = clean_instructions(inst, to_lower=True)
    byte_codes = parse(cleaned_inst)
    return "\n".join([byte_code.to_assembly() for byte_code in byte_codes])


if __name__ == '__main__':
    with open(SIMPLE_ADD) as f:
        inst = f.read()

    with open(SIMPLE_ADD_ASM, "w") as f:
        s = translate(inst)
        f.write(s)
        print(s)
