import pathlib

from translator.parser import parse, clean_instructions

PROJECT_07_DIR = pathlib.Path("/home/miguel/nand2tetris/projects/07")
SIMPLE_ADD_DIR = PROJECT_07_DIR / pathlib.Path("StackArithmetic/SimpleAdd")
TEST_CODE_DIR = PROJECT_07_DIR / "test_code"

SIMPLE_ADD = SIMPLE_ADD_DIR / "SimpleAdd.vm"
SIMPLE_ADD_ASM = SIMPLE_ADD_DIR / "SimpleAdd.asm"

TEST_EQ = TEST_CODE_DIR / "test_eq/test_eq.vm"
TEST_EQ_ASM = TEST_CODE_DIR / "test_eq/test_eq.asm"

TEST_LT = TEST_CODE_DIR / "test_lt/test_lt.vm"
TEST_LT_ASM = TEST_CODE_DIR / "test_lt/test_lt.asm"


def translate(inst: str) -> str:
    cleaned_inst = clean_instructions(inst, to_lower=True)
    byte_codes = parse(cleaned_inst)
    return "\n".join([byte_code.to_asm() for byte_code in byte_codes])


if __name__ == "__main__":
    with open(TEST_EQ) as f:
        inst = f.read()

    with open(TEST_EQ_ASM, "w") as f:
        s = translate(inst)
        f.write(s)
        print(s)
