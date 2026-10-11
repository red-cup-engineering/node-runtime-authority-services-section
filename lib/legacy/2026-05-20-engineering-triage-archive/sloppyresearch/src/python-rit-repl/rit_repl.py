# rit_repl.py — Relational Infinity-Topos REPL (canonical lax-idempotent Flow)
from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, FrozenSet, Iterable, Dict, Set, Tuple, List

Rel = FrozenSet[str]
Universe = FrozenSet[str]

# ---------- basic set logic ----------
def entails(a: Rel, b: Rel) -> bool: return a.issubset(b)
def together(a: Rel, b: Rel) -> Rel: return a & b
def either(a: Rel, b: Rel) -> Rel: return a | b
def negate(U: Universe, a: Rel) -> Rel: return U - a
def implies(U: Universe, b: Rel, c: Rel) -> Rel: return negate(U,b) | c

# ---------- closure & adjoint open ----------
def closure_by_neighborhood(U: Universe, adj: Dict[str, Set[str]]) -> Callable[[Rel], Rel]:
    N = {x:set(adj.get(x,{x}))|{x} for x in U}
    for x in U:
        for y in list(N[x]): N.setdefault(y,set()).add(x)
    @lru_cache(maxsize=None)
    def close(a: Rel) -> Rel:
        cur=set(a);changed=True
        while changed:
            changed=False
            for x in list(cur):
                for y in N.get(x,{x}):
                    if y not in cur and y in U: cur.add(y);changed=True
        return frozenset(cur)
    return close

def open_logic_as_left_adjoint(U: Universe, close: Callable[[Rel], Rel]) -> Callable[[Rel], Rel]:
    closed={c for c in powerset(U) if close(c)==c}
    @lru_cache(maxsize=None)
    def open_(a: Rel)->Rel:
        u=frozenset().union(*(c for c in closed if c.issubset(a)))
        r=close(close(u)&a)
        return frozenset(x for x in r if x in a)
    return open_

def powerset(U: Universe)->Set[Rel]:
    items=tuple(U);out=set()
    for mask in range(1<<len(items)):
        s=frozenset(items[i] for i in range(len(items)) if(mask>>i)&1)
        out.add(s)
    return out

# ---------- canonical Flow ----------
def flow_canonical(U: Universe,
                   open_logic: Callable[[Rel], Rel],
                   close: Callable[[Rel], Rel]) -> Callable[[Rel], Rel]:
    """
    Lax-idempotent comonadic Flow satisfying:
      - deflationary: Flow(x) ≤ x
      - monotone
      - lax-idempotent: Flow(Flow(x)) ≤ Flow(x)
      - core-preserving with May=Open, Must=Close
    Constructed as envelope of the balance pair: Flow(x)=Open(Close(x))∧Close(Open(x))
    """
    @lru_cache(maxsize=None)
    def flow(x: Rel)->Rel:
        oc=open_logic(close(x))
        co=close(open_logic(x))
        return together(oc,co)
    return flow

# ---------- algebra bundle ----------
@dataclass(frozen=True)
class Algebra:
    U: Universe
    close: Callable[[Rel],Rel]
    open_logic: Callable[[Rel],Rel]
    flow: Callable[[Rel],Rel]

def must(A: Algebra,x:Rel)->Rel: return A.close(x)
def may(A: Algebra,x:Rel)->Rel:  return A.open_logic(x)
def envelope(A: Algebra,x:Rel)->Rel: return together(may(A,x),must(A,x))
def step_flow(A: Algebra,x:Rel)->Rel: return A.flow(x)

# ---------- diagnostics ----------
def fixed_locus(A: Algebra)->Set[Rel]:
    return {a for a in powerset(A.U) if A.close(a)==a}
def balance_ok(A: Algebra,a:Rel)->Tuple[bool,bool,bool,bool]:
    o,c=may(A,a),must(A,a)
    return (entails(o,a),entails(a,c),A.close(o)==o,A.open_logic(c)==c)
def flow_props(A: Algebra,a:Rel)->Dict[str,bool]:
    f=A.flow(a);ff=A.flow(f)
    return {
        "deflationary": entails(f,a),
        "lax_idempotent": entails(ff,f),
        "fixed_point": f==a
    }

# ---------- world ----------
@dataclass
class World:
    A: Algebra
    states: Dict[str,Rel]

    def step(self,names:Iterable[str]=()):
        for k in list(names) or list(self.states.keys()):
            self.states[k]=step_flow(self.A,self.states[k])

# ---------- build default ----------
def default_world()->World:
    U=frozenset("abcdef")
    adj={
        "a":{"a","b"},
        "b":{"a","b","c"},
        "c":{"b","c","d"},
        "d":{"c","d","e"},
        "e":{"d","e","f"},
        "f":{"e","f"},
    }
    close=closure_by_neighborhood(U,adj)
    openL=open_logic_as_left_adjoint(U,close)
    flow=flow_canonical(U,openL,close)
    A=Algebra(U,close,openL,flow)
    states={"X":frozenset("ab"),"Y":frozenset("bd"),"Z":frozenset("ce")}
    return World(A,states)

# ---------- repl ----------
HELP=r"""
Commands:
  show               — show universe and states
  step [NAMES...]    — apply Flow to all or listed states
  close NAME         — NAME := Close(NAME)
  open NAME          — NAME := Open(NAME)
  flow NAME          — NAME := Flow(NAME)
  env NAME           — NAME := Envelope(NAME)
  laws               — check Balance and Flow properties on first state
  help, quit         — self-explanatory
"""

def pretty(r:Rel)->str: return "{"+"".join(sorted(r))+"}"

def print_world(w:World):
    print("Universe:", "".join(sorted(w.A.U)))
    print("Closed #:", len(fixed_locus(w.A)))
    for k,v in sorted(w.states.items()): print(f"  {k}={pretty(v)}")

def repl():
    w=default_world()
    print("RIT REPL — canonical lax-idempotent Flow. Type 'help' for commands.")
    print_world(w)
    while True:
        try: line=input("> ").strip()
        except EOFError: break
        if not line: continue
        if line in ("quit","exit"): break
        if line=="help": print(HELP); continue
        if line=="show": print_world(w); continue
        if line.startswith("step"):
            parts=line.split();names=parts[1:] if len(parts)>1 else []
            w.step(names);print("stepped.");print_world(w);continue
        if line.startswith("close "):
            n=line.split()[1];w.states[n]=must(w.A,w.states[n]);continue
        if line.startswith("open "):
            n=line.split()[1];w.states[n]=may(w.A,w.states[n]);continue
        if line.startswith("flow "):
            n=line.split()[1];w.states[n]=step_flow(w.A,w.states[n]);continue
        if line.startswith("env "):
            n=line.split()[1];w.states[n]=envelope(w.A,w.states[n]);continue
        if line=="laws":
            a=next(iter(w.states.values()))
            b1,b2,b3,b4=balance_ok(w.A,a)
            props=flow_props(w.A,a)
            print("Balance:",b1,b2,b3,b4)
            print("Flow:",props)
            continue
        print("unknown. type help.")
    print("bye.")

if __name__=="__main__":
    repl()
