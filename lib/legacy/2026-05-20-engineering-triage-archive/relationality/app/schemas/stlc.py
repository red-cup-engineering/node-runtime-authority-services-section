"""Simply-typed lambda calculus (STLC) schemas.

These datatypes reflect the state representation from the
Simply-Typed Lambda Simulation specification: term and type
ASTs plus typing contexts.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class TypeAST(BaseModel):
    """Type AST for STLC.

    Minimal grammar:
    - atom: named base type,
    - arrow: function type A -> B.
    Fixpoint/type-former support can be added later.
    """

    kind: Literal["atom", "arrow"] = Field(
        ..., description="Type constructor kind"
    )
    name: Optional[str] = Field(
        default=None,
        description="Base type name (for atom)",
    )
    left: Optional["TypeAST"] = Field(
        default=None,
        description="Domain type (for arrow)",
    )
    right: Optional["TypeAST"] = Field(
        default=None,
        description="Codomain type (for arrow)",
    )


TypeAST.model_rebuild()


class TermAST(BaseModel):
    """Term AST for STLC.

    Minimal grammar:
    - var: variable reference,
    - lam: λx:A. t,
    - app: t u.
    Fixpoint constructs can be added as separate kinds later.
    """

    kind: Literal["var", "lam", "app"] = Field(
        ..., description="Term constructor kind"
    )
    var: Optional[str] = Field(
        default=None,
        description="Variable name (for var, lam)",
    )
    type: Optional[TypeAST] = Field(
        default=None,
        description="Annotated type (for lam, optional elsewhere)",
    )
    body: Optional["TermAST"] = Field(
        default=None,
        description="Body term (for lam)",
    )
    func: Optional["TermAST"] = Field(
        default=None,
        description="Function term (for app)",
    )
    arg: Optional["TermAST"] = Field(
        default=None,
        description="Argument term (for app)",
    )


TermAST.model_rebuild()


class TypingContextEntry(BaseModel):
    """Single (variable, type) entry in a typing context."""

    var: str = Field(..., description="Variable name")
    type: TypeAST = Field(..., description="Type of the variable")


class TypingContext(BaseModel):
    """Finite typing context Γ as a sequence of entries."""

    entries: List[TypingContextEntry] = Field(
        default_factory=list,
        description="Context entries",
    )

