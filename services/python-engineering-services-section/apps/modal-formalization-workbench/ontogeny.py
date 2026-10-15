#!/usr/bin/env python3
# ontogeny.py
# Single-file idle-sim module: "Ontogeny — Slime -> Crystal"
# No external dependencies, no adversaries. CLI + save/load.
# Theme:
#  - Slime phase: closure = diffusion (up-closure), interior = retraction
#  - Crystal phase: closure = growth layers, interior = anneal
# Mechanics:
#  - Deck of nuclei/axes you cycle through each tick ("pulses")
#  - Energy from shrinkage of the fixpoint family
#  - Viscosity/Stress rises with noncommutation; purge by spending Energy
#  - Prestige yields Memory; unlocks more deck slots and mild buffs
#  - Optional DOT export of tower-size evolution for the current deck

from __future__ import annotations
import json, os, time, random, sys
from typing import List, Callable, Tuple, Dict, Optional

# ------------- Finite-set / powerset utilities -------------

class Universe:
    def __init__(self, elems: List[int]):
        self.U: Tuple[int, ...] = tuple(_uniq(elems))
    # set operations over frozensets of elements from U
    def empty(self) -> frozenset: return frozenset()
    def is_set(self, s: frozenset) -> bool: return isinstance(s, frozenset) and all(x in self.U for x in s)
    def eq(self, a: frozenset, b: frozenset) -> bool: return a == b
    def union(self, a: frozenset, b: frozenset) -> frozenset: return a | b
    def inter(self, a: frozenset, b: frozenset) -> frozenset: return a & b
    def diff(self, a: frozenset, b: frozenset) -> frozenset: return a - b
    def complement(self, a: frozenset) -> frozenset: return frozenset(self.U) - a
    def power_set(self) -> List[frozenset]:
        U = list(self.U); n = len(U)
        out = []
        for mask in range(1<<n):
            s = frozenset(U[i] for i in range(n) if (mask>>i)&1)
            out.append(s)
        return out

def _uniq(xs):
    seen=set(); out=[]
    for x in xs:
        if x not in seen:
            seen.add(x); out.append(x)
    return out

# ------------- Heyting algebra bits (powerset over finite U) -------------

def heyting_implication(U: Universe) -> Callable[[frozenset, frozenset], frozenset]:
    # In P(E), A ⇒ B = (¬A) ∪ B
    def impl(A: frozenset, B: frozenset) -> frozenset:
        return U.union(U.complement(A), B)
    return impl

def interior_from_closure(U: Universe, c: Callable[[frozenset], frozenset]) -> Callable[[frozenset], frozenset]:
    return lambda A: U.complement(c(U.complement(A)))

def fixpoints(c: Callable[[frozenset], frozenset], subsets: List[frozenset]) -> List[frozenset]:
    return [a for a in subsets if c(a) == a]

# ------------- Preorders and induced closures -------------

def random_preorder(n: int, p: float, rng: random.Random) -> Callable[[int,int], bool]:
    edges = [[False]*n for _ in range(n)]
    for i in range(n): edges[i][i] = True
    for i in range(n):
        for j in range(i+1, n):
            if rng.random() < p:
                edges[i][j] = True
    # transitive closure (Floyd–Warshall-ish)
    for k in range(n):
        for i in range(n):
            if edges[i][k]:
                rowk = edges[k]
                rowi = edges[i]
                for j in range(n):
                    if rowk[j]: rowi[j] = True
    return lambda x,y: edges[x][y]

def up_closure(U: Universe, leq: Callable[[int,int],bool]) -> Callable[[frozenset], frozenset]:
    def c(A: frozenset) -> frozenset:
        out = set(A)
        for x in list(A):
            for y in U.U:
                if leq(x,y): out.add(y)
        return frozenset(out)
    return c

def down_closure(U: Universe, leq: Callable[[int,int],bool]) -> Callable[[frozenset], frozenset]:
    def c(A: frozenset) -> frozenset:
        out = set(A)
        for x in list(A):
            for y in U.U:
                if leq(y,x): out.add(y)
        return frozenset(out)
    return c

# ------------- Closure tower & commutation metrics -------------

def closure_tower(nuclei: List[Callable[[frozenset], frozenset]], subsets: List[frozenset]) -> Tuple[List[List[frozenset]], int]:
    # iterate the nuclei cyclically; record fixpoint families and stop when the family stabilizes
    fams: List[List[frozenset]] = [list(subsets)]
    idx = 0
    while True:
        c = nuclei[idx % len(nuclei)]
        fix = fixpoints(c, fams[-1])
        # stabilized as families?
        if _same_family(fams[-1], fix):
            break
        fams.append(fix)
        idx += 1
        if idx > 1000:  # hard stop for safety
            break
    return fams, idx

def _same_family(a: List[frozenset], b: List[frozenset]) -> bool:
    return len(a) == len(b) and set(a) == set(b)

def commute_rate(nuclei: List[Callable[[frozenset],frozenset]], subsets: List[frozenset], samples: int = 200) -> float:
    # crude: for random A, test c1(c2(A)) == c2(c1(A)) across random pairs
    if len(nuclei) < 2: return 1.0
    rng = random.Random(1337)
    pairs = []
    for _ in range(samples):
        i = rng.randrange(len(nuclei))
        j = rng.randrange(len(nuclei))
        if i == j: continue
        pairs.append((i,j))
    hits = 0; trials = 0
    for i,j in pairs:
        A = rng.choice(subsets)
        trials += 1
        if nuclei[i](nuclei[j](A)) == nuclei[j](nuclei[i](A)): hits += 1
    return hits / max(1, trials)

# ------------- Deck elements (enzymes/axes) -------------

class Nucleus:
    def __init__(self, name: str, fn: Callable[[frozenset], frozenset], tag: str = "generic"):
        self.name = name
        self.fn = fn
        self.tag = tag  # "up", "down", "slice", "idemp", "noise"

# helper to slice-guard a closure
def slice_guard(U: Universe, base: Callable[[frozenset], frozenset], max_size: int) -> Callable[[frozenset], frozenset]:
    def c(A: frozenset) -> frozenset:
        if len(A) <= max_size: return base(A)
        return A
    return c

# ------------- Game model -------------

class Game:
    def __init__(self, n: int = 5, seed: Optional[int] = None):
        self.rng = random.Random(seed if seed is not None else int(time.time()))
        # universe and algebra
        self.U = Universe(list(range(n)))
        self.ps = self.U.power_set()
        self.impl = heyting_implication(self.U)
        # base preorder ≤, plus additional learned
        self.base_leq = lambda x,y: x <= y
        self.learned_preorders: List[Callable[[int,int],bool]] = []
        # initial deck (slime style): up/down for base preorder
        self.deck: List[Nucleus] = []
        self._seed_base_deck()
        # cycle pointer and family state
        self.ptr = 0
        self.family: List[frozenset] = list(self.ps)
        self.prev_size = len(self.family)
        # resources
        self.energy = 0         # slime: Biomass, crystal: Thermal energy
        self.memory = 0         # spores/inclusions across prestiges
        self.tier = 1
        # environment / rates
        self.auto_rate = 0.0    # pulses per second
        self.offline_cap = 7200 # seconds
        self.last_time = time.time()
        # costs and caps
        self.cost_new_pre = 10
        self.cost_slot = 25
        self.cost_auto = 20
        self.max_slots = 2
        # phase: "slime" | "crystal"
        self.phase = "slime"
        # tension: viscosity (slime) / stress (crystal)
        self.tension = 0.0
        # multipliers
        self.prod_mult = 1.0
        self.tension_growth = 1.0
        # synergy counters
        self.up_count = 1
        self.down_count = 1

    # ---- deck seed ----
    def _seed_base_deck(self):
        cf = up_closure(self.U, self.base_leq)
        cb = down_closure(self.U, self.base_leq)
        self.deck = [
            Nucleus("Up[≤]", cf, tag="up"),
            Nucleus("Down[≤]", cb, tag="down")
        ]
        self.max_slots = 2
        self.up_count = 1; self.down_count = 1

    # ---- tick/pulse ----
    def _apply_one(self) -> int:
        if not self.deck: return 0
        c = self.deck[self.ptr % len(self.deck)].fn
        fix = fixpoints(c, self.family)
        before, after = len(self.family), len(fix)
        self.family = fix
        self.ptr += 1
        # energy from shrinkage
        base_gain = max(0, before - after)
        return base_gain

    def _deck_commute_deficit(self) -> float:
        # 1 - commute rate
        return 1.0 - commute_rate([n.fn for n in self.deck], self.ps, samples=120)

    def _production_multiplier(self) -> float:
        # tier increases, phase-specific bonuses, and simple set-bonus synergies
        m = self.prod_mult * max(1.0, float(self.tier))
        # synergy: 2+ ups add mild speed, 2+ downs add mild efficiency
        if self.up_count >= 2: m *= 1.10
        if self.down_count >= 2: m *= 1.10
        if self.phase == "crystal": m *= 1.10   # crystal is slightly more efficient at scale
        return m

    def pulse(self) -> Dict[str, float]:
        base = self._apply_one()
        self.energy += int(base * self._production_multiplier())
        stabilized = (len(self.family) == self.prev_size)
        self.prev_size = len(self.family)
        # tension growth from noncommutation
        deficit = self._deck_commute_deficit()
        phase_k = 1.0 if self.phase == "slime" else 1.2
        self.tension += deficit * 0.5 * self.tension_growth * phase_k
        return {"base_gain": base, "stabilized": 1 if stabilized else 0, "tension": self.tension}

    def run_pulses(self, N: int) -> int:
        tot = 0
        for _ in range(max(0, N)):
            tot += self.pulse()["base_gain"]
        return tot

    def process_offline(self) -> Tuple[int,int]:
        now = time.time()
        dt = min(self.offline_cap, max(0.0, now - self.last_time))
        ticks = int(self.auto_rate * dt)
        base = self.run_pulses(ticks)
        self.last_time = now
        return ticks, base

    # ---- economy actions ----
    def buy_preorder(self) -> bool:
        if self.energy < self.cost_new_pre: return False
        self.energy -= self.cost_new_pre
        self.cost_new_pre = int(self.cost_new_pre * 1.8) + 3
        n = len(self.U.U)
        leq = random_preorder(n, self.rng.uniform(0.25,0.55), self.rng)
        self.learned_preorders.append(leq)
        # add both up and down closures as options
        self._add_to_deck(Nucleus(f"Up[R{len(self.learned_preorders)}]", up_closure(self.U, leq), tag="up"))
        self._add_to_deck(Nucleus(f"Down[R{len(self.learned_preorders)}]", down_closure(self.U, leq), tag="down"))
        return True

    def buy_slot(self) -> bool:
        if self.energy < self.cost_slot: return False
        self.energy -= self.cost_slot
        self.cost_slot = int(self.cost_slot * 2.0) + 7
        self.max_slots = min(8, self.max_slots + 1)
        return True

    def buy_auto(self) -> bool:
        if self.energy < self.cost_auto: return False
        self.energy -= self.cost_auto
        self.cost_auto = int(self.cost_auto * 2.2) + 9
        self.auto_rate = round(self.auto_rate + 0.5, 2)
        return True

    def purge_tension(self, amount: float = 3.0) -> bool:
        # spends energy to reduce tension
        cost = int(10 * amount)
        if self.energy < cost: return False
        self.energy -= cost
        self.tension = max(0.0, self.tension - amount)
        return True

    # ---- deck mgmt ----
    def _add_to_deck(self, nuc: Nucleus):
        # append if we haven't exceeded max slots
        if len(self.deck) < self.max_slots:
            self.deck.append(nuc)
            if nuc.tag == "up": self.up_count += 1
            if nuc.tag == "down": self.down_count += 1

    def list_deck(self) -> List[Tuple[int,str,str]]:
        return [(i, n.name, n.tag) for i, n in enumerate(self.deck)]

    def move(self, i: int, j: int) -> bool:
        if not (0 <= i < len(self.deck) and 0 <= j < len(self.deck)): return False
        self.deck[i], self.deck[j] = self.deck[j], self.deck[i]
        return True

    def cut(self, i: int) -> bool:
        if not (0 <= i < len(self.deck)): return False
        n = self.deck.pop(i)
        if n.tag == "up": self.up_count = max(0, self.up_count - 1)
        if n.tag == "down": self.down_count = max(0, self.down_count - 1)
        return True

    def add_slice_enzyme(self, base: str, max_size: int) -> bool:
        # base is "up" or "down" on base preorder
        if base not in ("up","down"): return False
        b = up_closure(self.U, self.base_leq) if base == "up" else down_closure(self.U, self.base_leq)
        g = slice_guard(self.U, b, max_size)
        return self._add_slice_impl(g, base, max_size)

    def _add_slice_impl(self, g: Callable[[frozenset],frozenset], base_tag: str, max_size: int) -> bool:
        if len(self.deck) >= self.max_slots: return False
        name = f"{'Up' if base_tag=='up' else 'Down'}-Slice(≤{max_size})"
        self.deck.append(Nucleus(name, g, tag="slice"))
        return True

    # ---- phases and prestige ----
    def transform(self, phase: str) -> bool:
        # "slime" or "crystal"
        if phase not in ("slime","crystal"): return False
        self.phase = phase
        return True

    def prestige(self) -> int:
        # payout proportional to shrink and tier
        start, end = len(self.ps), len(self.family)
        payout = max(0, (start - end)//2) + self.tier
        self.memory += payout
        self.tier += 1
        self.prod_mult *= 1.05  # small permanent increase
        # reset lattice family and pointer, keep deck and learned bits
        self.family = list(self.ps)
        self.prev_size = len(self.family)
        self.ptr = 0
        self.tension = 0.0
        return payout

    # ---- derived stats ----
    def tower_sizes(self) -> List[int]:
        fams, _ = closure_tower([n.fn for n in self.deck], self.ps)
        return [len(f) for f in fams]

    def steps(self) -> int:
        _, idx = closure_tower([n.fn for n in self.deck], self.ps)
        return idx

    # ---- save/load ----
    def to_dict(self) -> Dict:
        return {
            "U": list(self.U.U),
            "deck": [{"name": n.name, "tag": n.tag} for n in self.deck],
            "learned": len(self.learned_preorders),  # count only (we regenerate random ones on load)
            "ptr": self.ptr,
            "family_size": len(self.family),
            "energy": self.energy,
            "memory": self.memory,
            "tier": self.tier,
            "auto_rate": self.auto_rate,
            "costs": {"pre": self.cost_new_pre, "slot": self.cost_slot, "auto": self.cost_auto},
            "max_slots": self.max_slots,
            "phase": self.phase,
            "tension": self.tension,
            "prod_mult": self.prod_mult,
            "tension_growth": self.tension_growth,
        }

    def save(self, path: str) -> str:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        return path

    def load(self, path: str) -> bool:
        if not os.path.exists(path): return False
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        # rebuild U and base deck
        self.U = Universe(list(d.get("U", list(range(5)))))
        self.ps = self.U.power_set()
        self.impl = heyting_implication(self.U)
        self._seed_base_deck()
        # re-add learned preorders
        learned = int(d.get("learned", 0))
        for _ in range(learned):
            self.buy_preorder()
        # we don't persist slice enzymes exactly; users can re-add if desired
        self.ptr = int(d.get("ptr", 0))
        self.family = list(self.ps)   # reset family; deterministic restore is out of scope here
        self.prev_size = len(self.family)
        self.energy = int(d.get("energy", 0))
        self.memory = int(d.get("memory", 0))
        self.tier = int(d.get("tier", 1))
        self.auto_rate = float(d.get("auto_rate", 0.0))
        c = d.get("costs", {})
        self.cost_new_pre = int(c.get("pre", 10))
        self.cost_slot = int(c.get("slot", 25))
        self.cost_auto = int(c.get("auto", 20))
        self.max_slots = int(d.get("max_slots", 2))
        self.phase = d.get("phase", "slime")
        self.tension = float(d.get("tension", 0.0))
        self.prod_mult = float(d.get("prod_mult", 1.0))
        self.tension_growth = float(d.get("tension_growth", 1.0))
        return True

    # ---- status & DOT ----
    def status(self) -> str:
        sizes = self.tower_sizes()
        return (
            f"Form={self.phase} | U={len(self.U.U)} | deck={len(self.deck)}/{self.max_slots} | steps={self.steps()}\n"
            f"tower: {sizes}\n"
            f"energy={self.energy} | memory={self.memory} | tier={self.tier} | prod_mult={self.prod_mult:.2f}\n"
            f"auto={self.auto_rate}/s | tension={self.tension:.2f} | costs: pre={self.cost_new_pre} slot={self.cost_slot} auto={self.cost_auto}\n"
            f"deck: " + ", ".join(f"[{i}:{n.name}]" for i,n in enumerate(self.deck))
        )

    def dump_dot(self, path: str) -> str:
        sizes = self.tower_sizes()
        with open(path, "w", encoding="utf-8") as f:
            f.write("digraph Tower {\n  rankdir=LR;\n")
            for i,s in enumerate(sizes):
                f.write(f'  n{i} [label="H{i}\\n|H{i}|={s}"];\n')
            for i in range(len(sizes)-1):
                f.write(f"  n{i} -> n{i+1};\n")
            f.write("}\n")
        return path

# ------------- CLI -------------

HELP = """
Commands:
  status                        Show state
  pulse                         Apply one deck nucleus; gain energy from shrinkage
  run N                         Run N pulses
  buy pre                       Buy a random preorder (adds Up/Down nuclei), cost: energy
  buy slot                      Increase deck size cap, cost: energy
  buy auto                      Increase auto pulses/sec by 0.5, cost: energy
  purge [x]                     Spend energy to reduce tension (default x=3.0)
  deck                          List deck
  move I J                      Swap deck positions I and J
  cut I                         Remove deck slot I
  add slice up|down K           Add slice enzyme acting only on sets of size ≤ K (base preorder)
  transform slime|crystal       Switch phase
  prestige                      Reset family; gain memory; +5%% permanent production
  save FILE.json                Save game
  load FILE.json                Load game (rebuilds learned preorders randomly)
  dot FILE.dot                  Export DOT of tower sizes
  help                          Show help
  quit                          Exit
"""

def main():
    # minimal TUI
    g = Game(n=5)
    save_default = os.path.join(os.getcwd(), "ontogeny_save.json")
    print("Ontogeny — Slime -> Crystal. Type 'help'.")
    while True:
        try:
            cmd = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye.")
            break

        # offline pulses
        ticks, base = g.process_offline()
        if ticks > 0:
            print(f"[offline] {ticks} pulses, base {base}, energy {g.energy}")

        if not cmd:
            continue
        parts = cmd.split()
        op = parts[0].lower()

        if op == "help":
            print(HELP)

        elif op == "status":
            print(g.status())

        elif op == "pulse":
            res = g.pulse()
            print(f"pulse: base +{res['base_gain']} | energy {g.energy} | tension {g.tension:.2f}")
            if res["stabilized"]:
                print("stabilized step detected (no further shrink this pass). Consider prestige.")

        elif op == "run":
            if len(parts) < 2 or not parts[1].isdigit():
                print("usage: run N"); continue
            N = int(parts[1])
            base = g.run_pulses(N)
            print(f"ran {N} pulses | base {base} | energy {g.energy} | family {len(g.family)}")

        elif op == "buy":
            if len(parts) < 2:
                print("usage: buy pre|slot|auto"); continue
            what = parts[1].lower()
            if what == "pre":
                ok = g.buy_preorder(); print("bought preorder" if ok else "not enough energy")
            elif what == "slot":
                ok = g.buy_slot(); print("deck slot +1" if ok else "not enough energy")
            elif what == "auto":
                ok = g.buy_auto(); print("auto rate increased" if ok else "not enough energy")
            else:
                print("unknown buy option")

        elif op == "purge":
            amount = 3.0
            if len(parts) >= 2:
                try: amount = float(parts[1])
                except: pass
            ok = g.purge_tension(amount)
            print("purged" if ok else "not enough energy")

        elif op == "deck":
            listing = g.list_deck()
            if not listing:
                print("deck empty")
            else:
                for i,name,tag in listing:
                    print(f"[{i}] {name} ({tag})")

        elif op == "move":
            if len(parts) < 3 or not parts[1].isdigit() or not parts[2].isdigit():
                print("usage: move I J"); continue
            i, j = int(parts[1]), int(parts[2])
            print("ok" if g.move(i,j) else "invalid indices")

        elif op == "cut":
            if len(parts) < 2 or not parts[1].isdigit():
                print("usage: cut I"); continue
            i = int(parts[1])
            print("removed" if g.cut(i) else "invalid index")

        elif op == "add":
            if len(parts) < 4 or parts[1].lower() != "slice":
                print("usage: add slice up|down K"); continue
            base = parts[2].lower()
            try:
                K = int(parts[3])
            except:
                print("K must be integer"); continue
            ok = g.add_slice_enzyme(base, K)
            print("added" if ok else "failed (deck full or bad type)")

        elif op == "transform":
            if len(parts) < 2 or parts[1].lower() not in ("slime","crystal"):
                print("usage: transform slime|crystal"); continue
            ok = g.transform(parts[1].lower()); print("ok" if ok else "failed")

        elif op == "prestige":
            earned = g.prestige()
            print(f"prestige: +{earned} memory | tier {g.tier} | prod_mult {g.prod_mult:.2f}")

        elif op == "save":
            path = parts[1] if len(parts) >= 2 else save_default
            out = g.save(path)
            print("saved to", out)

        elif op == "load":
            path = parts[1] if len(parts) >= 2 else save_default
            ok = g.load(path)
            print("loaded" if ok else "no save found")

        elif op == "dot":
            if len(parts) < 2:
                print("usage: dot FILE.dot"); continue
            path = g.dump_dot(parts[1])
            print("wrote", path)

        elif op == "quit":
            print("bye."); break

        else:
            print("unknown command. type 'help'")

if __name__ == "__main__":
    main()
