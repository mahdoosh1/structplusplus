from dataclasses import dataclass
from typing import Optional, Union
from enum import Enum, auto
from lexer import TokenType
Pos = tuple[int, int]

class NumberKind(Enum):
    INTEGER = auto()
    FLOAT = auto()
    SIZE = auto()

# --- expressions ---
@dataclass
class Expression:
    pos: Pos

@dataclass
class CallExpression(Expression):
    args: list[Expression]

@dataclass
class Identifier(Expression):
    name: str

@dataclass
class NumberLiteral(Expression):
    raw: str   # keep original text (integers, floats, sizes like "2B")
    kind: Union[str, TokenType]  # "integer"|"float"|"size"

@dataclass
class Size(Expression):
    value: Union[str, NumberLiteral]
@dataclass
class StringLiteral(Expression):
    value: str

@dataclass
class FieldAccess(Expression):
    target: Expression   # typically Identifier or another FieldAccess
    field: str

@dataclass
class BinaryOp(Expression):
    left: Expression
    op: str
    right: Expression

@dataclass
class UnaryOp(Expression):
    op: str
    operand: Expression

# --- statements / declarations ---
@dataclass
class Statement:
    pos: Pos

@dataclass
class RaiseStmt(Statement):
    message: StringLiteral

@dataclass
class DeclareStatement(Statement):
    # can be: ident ":" ident | size [ "[" ( ident | number | size ) "]" ] | [ "=" ( ident | number ) ]
    name: Identifier        # identifier when present (for ident:ident form or named field)
    type: Expression   # type name when present (like uint32)
    array_size: Optional[Expression]  # expression inside brackets or None
    default: Optional[Expression]

@dataclass
class SpecialLocal(Statement):
    name: str   # "reserve" / "noreserve" / "endian"
    arg: Optional[str]   # "front"/"behind"/"big"/"little" or None

# --- condition / flow ---
@dataclass
class Block(Statement):
    statements: list[Union[Statement, 'ConditionalBlock']]

@dataclass
class ConditionalBlock(Block):
    condition: Expression

@dataclass
class IfThenElse(Statement):
    if_: ConditionalBlock
    elif_: list[ConditionalBlock]
    else_: Optional[Block]

# --- preprocessor / global special ---
@dataclass
class Preprocessor:
    name: str
    args: list[str]

@dataclass
class SpecialGlobal(Statement):
    name: str
    arg: Optional[str]

# --- struct / top-level ---
@dataclass
class Struct(Statement):
    name: str
    params: list[Identifier]
    block: Block

@dataclass
class Program:
    items: list[Union[Struct, Preprocessor, SpecialGlobal]]
