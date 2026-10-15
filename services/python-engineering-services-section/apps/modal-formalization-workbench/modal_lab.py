#!/usr/bin/env python3
# modal_lab.py (v3): Modal formula engine with named modalities, axiom packs, and helpers.
# Works on top of ritm_core.py (finite powerset Heyting algebra with nuclei/interiors).

from __future__ import annotations
import re, os, sys, importlib.util
from typing import Dict, Callable, Optional, Tuple, List

# ---------- Load ritm_core ----------
HERE = os.path.dirname(os.path.abspath(__file__))
_CANDIDATES = [os.path.join(HERE, "ritm_core.py"), os.path.join("/mnt/data","ritm_core.py")]
_modpath = next((p for p in _CANDIDATES if os.path.exists(p)), None)
if not _modpath:
    raise RuntimeError("modal_lab: ritm_core.py not found next to this file")
spec = importlib.util.spec_from_file_location("ritm_core", _modpath)
ritm_core = importlib.util.module_from_spec(spec)  # type: ignore
sys.modules["ritm_core"] = ritm_core  # type: ignore
spec.loader.exec_module(ritm_core)  # type: ignore

# ---------- Lexer / Parser ----------
Token = Tuple[str,str]

def tokenize(s: str) -> List[Token]:
    specs = [
        ('SKIP',  r'\s+'),
        ('BOXF',  r'\[\]f'), ('BOXB', r'\[\]b'),
        ('DIAF',  r'<>f'),  ('DIAB', r'<>b'),
        ('BOX',   r'\[\]'), ('DIA',  r'<>'),
        ('NEG',   r'~'),
        ('AND',   r'&'),
        ('OR',    r'\|'),
        ('IMP',   r'->'),
        ('LP',    r'\('),
        ('RP',    r'\)'),
        ('ID',    r'[A-Za-z_][A-Za-z0-9_]*'),
    ]
    rx = '|'.join('(?P<%s>%s)' % p for p in specs)
    out: List[Token] = []
    pos = 0
    for m in re.finditer(rx, s):
        k = m.lastgroup; v = m.group()
        if k != 'SKIP':
            out.append((k, v))
        pos = m.end()
    if pos != len(s):
        raise SyntaxError(f"modal_lab: bad token at {pos}")
    return out

class Parser:
    # Precedence: ~,[],<> > & > | > -> (right-assoc for ->)
    def __init__(self, toks: List[Token]):
        self.t = toks; self.i = 0
    def peek(self) -> Optional[Token]:
        return self.t[self.i] if self.i < len(self.t) else None
    def take(self, kind: Optional[str]=None) -> Token:
        tok = self.peek()
        if tok is None:
            raise SyntaxError("modal_lab: unexpected EOF")
        if kind and tok[0] != kind:
            raise SyntaxError(f"modal_lab: expected {kind}, got {tok}")
        self.i += 1
        return tok
    def parse(self):
        return self._imp()
    def _imp(self):
        left = self._or()
        t = self.peek()
        if t and t[0] == 'IMP':
            self.take('IMP')
            right = self._imp()
            return ('IMP', left, right)
        return left
    def _or(self):
        left = self._and()
        while True:
            t = self.peek()
            if t and t[0] == 'OR':
                self.take('OR')
                right = self._and()
                left = ('OR', left, right)
            else:
                return left
    def _and(self):
        left = self._un()
        while True:
            t = self.peek()
            if t and t[0] == 'AND':
                self.take('AND')
                right = self._un()
                left = ('AND', left, right)
            else:
                return left
    def _un(self):
        t = self.peek()
        if t and t[0] in ('NEG','BOX','DIA','BOXF','BOXB','DIAF','DIAB'):
            self.take(t[0])
            sub = self._un()
            return (t[0], sub)
        if t and t[0] == 'LP':
            self.take('LP')
            node = self.parse()
            self.take('RP')
            return node
        if t and t[0] == 'ID':
            self.take('ID')
            return ('ID', t[1])
        raise SyntaxError(f"modal_lab: unexpected token {t}")

def parse(s: str):
    return Parser(tokenize(s)).parse()

# ---------- Builder / Semantics ----------
def build(U: "ritm_core.Universe", leq) -> Dict:
    cf = U.up_closure(leq)
    cb = U.down_closure(leq)
    i_f, i_b = ritm_core.interiors_forward_backward(cf, cb, U)
    impl = ritm_core.heyting_implication(U)

    def eval_ast(ast, env: Dict[str, frozenset], mode: str = 'forward') -> frozenset:
        k = ast[0]
        if k == 'ID':
            return env.get(ast[1], frozenset())
        if k == 'NEG':
            return U.complement(eval_ast(ast[1], env, mode))
        if k in ('BOX','BOXF'):   # □f
            return i_f(eval_ast(ast[1], env, mode))
        if k == 'BOXB':           # □b
            return i_b(eval_ast(ast[1], env, mode))
        if k in ('DIA','DIAF'):   # ◇f
            return cf(eval_ast(ast[1], env, mode))
        if k == 'DIAB':           # ◇b
            return cb(eval_ast(ast[1], env, mode))
        if k == 'AND':
            A = eval_ast(ast[1], env, mode)
            B = eval_ast(ast[2], env, mode)
            return U.intersection(A, B)
        if k == 'OR':
            A = eval_ast(ast[1], env, mode)
            B = eval_ast(ast[2], env, mode)
            return U.union(A, B)
        if k == 'IMP':
            A = eval_ast(ast[1], env, mode)
            B = eval_ast(ast[2], env, mode)
            return impl(A, B)
        raise ValueError("modal_lab: bad AST")

    def holds(ast, env, mode: str = 'forward') -> bool:
        return eval_ast(ast, env, mode) == frozenset(U.U)

    return {
        'eval':  eval_ast,
        'parse': parse,
        'holds': holds,
        'modes': ['forward', 'backward']  # named []f/<>f, []b/<>b also supported inside formulas
    }

# ---------- Axiom packs ----------
AXIOM_PACKS: Dict[str, List[str]] = {
    "T":   ["([]p) -> p"],
    "4":   ["([]p) -> ([]([]p))"],
    "K":   ["([](p->q)) -> (([]p)->([]q))"],
    "D":   ["([]p) -> (<>p)"],
    "Dual":["([]p) -> (~(<>(~p)))"],
    "S4":  ["([]p) -> p", "([]p) -> ([]([]p))", "([](p->q)) -> (([]p)->([]q))"],
    "S5":  ["([]p) -> p", "([]p) -> ([]([]p))", "(<>p) -> ([]<>p)"]
}

def pack_holds(pack: str, U: "ritm_core.Universe", leq, env: Dict[str,frozenset], mode='forward') -> bool:
    if pack not in AXIOM_PACKS:
        raise KeyError(f"Unknown axiom pack {pack}")
    sem = build(U, leq)
    return all(sem['holds'](sem['parse'](ax), env, mode) for ax in AXIOM_PACKS[pack])

if __name__ == "__main__":
    # Minimal smoke test
    U = ritm_core.Universe([0,1,2,3])
    env = {'p': frozenset([0,1]), 'q': frozenset([2,3])}
    ok = pack_holds("T", U, lambda x,y: x<=y, env)
    print("T holds (forward):", ok)
