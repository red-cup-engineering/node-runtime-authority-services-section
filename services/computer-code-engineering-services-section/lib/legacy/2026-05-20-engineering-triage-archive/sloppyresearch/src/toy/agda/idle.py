#!/usr/bin/env python3
# ritm_idle_plus.py (v3)
# Idle game built on ritm_core + modal_lab with:
#  - Auto-ticks and offline progress
#  - Save / Load
#  - Auto-prestige policies (string rules)
#  - Artifacts from high-step towers
#  - Axiom assertions for buffs; axiom tree (S4/S5 unlocks unique artifacts)
#  - Challenges 2.0 (daily seed, time trials, no-preorder run)
#  - Visualizer: dump a DOT graph of nuclei cycle and tower sizes
#
# No external deps. CLI.

from __future__ import annotations
import importlib.util, sys, os, time, random, json, datetime
from typing import List, Callable, Tuple, Dict, Optional

# ---------- Load ritm_core ----------
HERE = os.path.dirname(os.path.abspath(__file__))
CORE = next((p for p in [os.path.join(HERE,"ritm_core.py"), os.path.join("/mnt/data","ritm_core.py")] if os.path.exists(p)), None)
if CORE is None:
    print("ritm_core.py not found"); sys.exit(1)
spec = importlib.util.spec_from_file_location("ritm_core", CORE)
ritm_core = importlib.util.module_from_spec(spec)  # type: ignore
sys.modules["ritm_core"] = ritm_core  # type: ignore
spec.loader.exec_module(ritm_core)  # type: ignore

# ---------- Load modal_lab (optional but recommended) ----------
ML = next((p for p in [os.path.join(HERE,"modal_lab.py"), os.path.join("/mnt/data","modal_lab.py")] if os.path.exists(p)), None)
modal_lab = None
if ML:
    spec2 = importlib.util.spec_from_file_location("modal_lab", ML)
    modal_lab = importlib.util.module_from_spec(spec2)  # type: ignore
    sys.modules["modal_lab"] = modal_lab  # type: ignore
    spec2.loader.exec_module(modal_lab)  # type: ignore

SAVEFILE = os.path.join(HERE, "ritm_idle_save.json")

# ---------- Data classes ----------
class Artifact:
    def __init__(self, name: str, steps: int, mult: float, tag: str = "generic"):
        self.name = name
        self.steps = steps
        self.mult = mult
        self.tag = tag  # e.g., "S4", "S5", "generic"
    def to_dict(self): return {"name": self.name, "steps": self.steps, "mult": self.mult, "tag": self.tag}
    @staticmethod
    def from_dict(d): return Artifact(d["name"], d["steps"], d["mult"], d.get("tag","generic"))

class Challenge:
    def __init__(self, name: str, desc: str, key: str, reward: int):
        self.name = name
        self.desc = desc
        self.key = key              # internal key
        self.reward = reward
        self.done = False

# ---------- Utility: random preorder ----------
def random_preorder(n: int, p: float, rng: random.Random):
    edges = [[False]*n for _ in range(n)]
    for i in range(n): edges[i][i] = True
    for i in range(n):
        for j in range(i+1, n):
            if rng.random() < p: edges[i][j] = True
    # transitive closure
    for k in range(n):
        for i in range(n):
            if edges[i][k]:
                for j in range(n):
                    if edges[k][j]: edges[i][j] = True
    def leq(x,y): return edges[x][y]
    return leq

# ---------- Game ----------
class Game:
    def __init__(self, n=5, seed: Optional[int]=None):
        # daily seed for challenges
        if seed is None:
            today = datetime.date.today()
            seed = (today.year*73856093) ^ (today.month*19349663) ^ (today.day*83492791)
        self.rng = random.Random(seed)
        # universe and base preorder
        self.U = ritm_core.Universe(list(range(n)))
        self.ps = self.U.power_set()
        self.base_leq = lambda x,y: x<=y
        self.cf = self.U.up_closure(self.base_leq)
        self.cb = self.U.down_closure(self.base_leq)
        # nuclei cycle (start with forward/backward)
        self.nuclei: List[Callable] = [self.cf, self.cb]
        self.cycle_idx = 0
        # closure family state
        self.family: List[frozenset] = list(self.ps)
        self.prev_size = len(self.family)
        # currencies
        self.coh = 0
        self.insight = 0
        self.tier = 1
        # rates
        self.speed = 1
        self.auto_rate = 0.0
        self.offline_cap = 7200
        self.last_time = time.time()
        # costs
        self.cost_pre = 10
        self.cost_spd = 15
        self.cost_auto = 25
        # buffs and gear
        self.buff_mult = 1.0
        self.artifacts: List[Artifact] = []
        self.equipped: Optional[Artifact] = None
        # auto-prestige policy
        self.ap_policy = "steps>=4 OR family<=2"  # editable policy string
        # modal setup
        self.mode = 'forward'
        self.env = self._make_default_env()
        # axiom tree progress
        self.axiom_flags = {"T": False, "4": False, "K": False, "D": False, "Dual": False, "S4": False, "S5": False}
        # challenges (daily/time/no-preorder)
        self.challenge_start = time.time()
        self.challenges = self._make_challenges()

    # ----- helpers -----
    def _make_default_env(self) -> Dict[str,frozenset]:
        n = len(self.U.U)
        left  = [x for x in self.U.U if x < n//2]
        right = [x for x in self.U.U if x >= n//2]
        evens = [x for x in self.U.U if x % 2 == 0]
        return {"p": frozenset(left), "q": frozenset(right), "r": frozenset(evens)}

    def _steps(self) -> int:
        _, idx = ritm_core.closure_tower(self.nuclei, self.ps)
        return idx

    def _tower_sizes(self) -> List[int]:
        fams, _ = ritm_core.closure_tower(self.nuclei, self.ps)
        return [len(f) for f in fams]

    def _apply_one(self) -> int:
        c = self.nuclei[self.cycle_idx % len(self.nuclei)]
        fix = ritm_core.fixpoints(c, self.family)
        self.cycle_idx += 1
        g = max(0, len(self.family) - len(fix))
        self.family = fix
        return g

    def _mult(self) -> float:
        art_mult = (self.equipped.mult if self.equipped else 1.0)
        return self.buff_mult * art_mult * max(1, self.tier)

    # ----- main actions -----
    def tick(self) -> Tuple[int, bool]:
        base = 0
        for _ in range(self.speed):
            base += self._apply_one()
        self.coh += int(base * self._mult())
        stabilized = (len(self.family) == self.prev_size)
        self.prev_size = len(self.family)
        self._artifact_check()
        self._check_challenges()
        return base, stabilized

    def process_offline(self) -> Tuple[int,int]:
        now = time.time()
        dt = min(self.offline_cap, max(0.0, now - self.last_time))
        ticks = int(self.auto_rate * dt)
        base = 0
        for _ in range(ticks):
            base += self._apply_one()
        self.coh += int(base * self._mult())
        self.last_time = now
        if ticks > 0:
            self._artifact_check()
            self._check_challenges()
            self._maybe_autoprestige()
        return ticks, base

    def prestige(self) -> int:
        start, end = len(self.ps), len(self.family)
        earn = (start - end)//2 + self.tier if end < start else 0
        self.insight += earn
        self.tier += 1
        self.buff_mult *= 1.05
        self.family = list(self.ps)
        self.prev_size = len(self.family)
        self.cycle_idx = 0
        return earn

    # ----- upgrades -----
    def buy_preorder(self) -> bool:
        if self.coh < self.cost_pre:
            return False
        self.coh -= self.cost_pre
        self.cost_pre = int(self.cost_pre*1.7) + 3
        n = len(self.U.U)
        leq = random_preorder(n, self.rng.uniform(0.2, 0.6), self.rng)
        self.nuclei += [self.U.up_closure(leq), self.U.down_closure(leq)]
        self._artifact_check()
        return True

    def buy_speed(self) -> bool:
        if self.coh < self.cost_spd:
            return False
        self.coh -= self.cost_spd
        self.cost_spd = int(self.cost_spd*1.9) + 5
        self.speed += 1
        return True

    def buy_auto(self) -> bool:
        if self.coh < self.cost_auto:
            return False
        self.coh -= self.cost_auto
        self.cost_auto = int(self.cost_auto*2.1) + 10
        self.auto_rate = round(self.auto_rate + 0.5, 2)
        return True

    # ----- artifacts & axiom tree -----
    def _artifact_check(self):
        s = self._steps()
        if s >= 4 and all(a.steps != s or a.tag != "generic" for a in self.artifacts):
            mult = 1.0 + min(0.6, 0.05*s)
            self.artifacts.append(Artifact(f"Relic of {s} Cuts", s, mult, tag="generic"))

    def equip(self, i: int) -> bool:
        if 0 <= i < len(self.artifacts):
            self.equipped = self.artifacts[i]
            return True
        return False

    def assert_axiom(self, formula: str, cost: int = 5) -> Tuple[bool,str]:
        if modal_lab is None:
            return False, "modal_lab.py is missing"
        if self.insight < cost:
            return False, "not enough insight"
        sem = modal_lab.build(self.U, self.base_leq)
        ast = sem['parse'](formula)
        ok = sem['holds'](ast, self.env, self.mode)
        self.insight -= cost
        if ok:
            self.buff_mult *= 1.05
            self._update_axiom_tree(formula)
            return True, "axiom holds; permanent +5% buff"
        return False, "axiom fails; no effect"

    def prove_pack(self, pack: str, cost: int = 15) -> Tuple[bool,str]:
        if modal_lab is None:
            return False, "modal_lab.py is missing"
        if self.insight < cost:
            return False, "not enough insight"
        self.insight -= cost
        try:
            ok = modal_lab.pack_holds(pack, self.U, self.base_leq, self.env, self.mode)
        except KeyError:
            return False, f"unknown axiom pack {pack}"
        if ok:
            self.axiom_flags[pack] = True
            # unlock unique artifacts
            if pack == "S4" and all(a.tag!="S4" for a in self.artifacts):
                self.artifacts.append(Artifact("Idempotent Lens (S4)", steps=4, mult=1.15, tag="S4"))
            if pack == "S5" and all(a.tag!="S5" for a in self.artifacts):
                self.artifacts.append(Artifact("Symmetry Prism (S5)", steps=5, mult=1.25, tag="S5"))
            # global production bump
            self.buff_mult *= 1.10
            return True, f"{pack} holds; +10% buff and unique artifact"
        return False, f"{pack} fails in this world"

    def _update_axiom_tree(self, formula: str):
        # crude detection for common axioms to flag progress
        normalized = formula.replace(" ", "")
        if normalized == "([]p)->p": self.axiom_flags["T"] = True
        if normalized == "([]p)->([]([]p))": self.axiom_flags["4"] = True
        if normalized == "([](p->q))->(([]p)->([]q))": self.axiom_flags["K"] = True
        if normalized == "([]p)->(<>p)": self.axiom_flags["D"] = True
        if normalized == "([]p)->(~(<>(~p)))": self.axiom_flags["Dual"] = True

    # ----- challenges 2.0 -----
    def _make_challenges(self) -> List[Challenge]:
        today = datetime.date.today()
        daily_key = f"daily-{today.isoformat()}"
        return [
            Challenge("Daily Collapse", "Reach steps>=5 today", "daily", reward=25),
            Challenge("Speed Demon", "Stabilize to family<=2 in under 30s realtime", "time30", reward=20),
            Challenge("Austere Run", "Reach steps>=4 with no extra preorders", "no-preorder", reward=30),
        ]

    def _check_challenges(self):
        steps = self._steps()
        # daily
        ch = next((c for c in self.challenges if c.key=="daily"), None)
        if ch and (not ch.done) and steps >= 5:
            ch.done = True; self.insight += ch.reward
        # time trial
        ch = next((c for c in self.challenges if c.key=="time30"), None)
        if ch and (not ch.done):
            if time.time() - self.challenge_start <= 30 and len(self.family) <= 2:
                ch.done = True; self.insight += ch.reward
        # no-preorder (only base cf, cb allowed)
        ch = next((c for c in self.challenges if c.key=="no-preorder"), None)
        if ch and (not ch.done):
            if len(self.nuclei) == 2 and steps >= 4:
                ch.done = True; self.insight += ch.reward

    # ----- auto-prestige policy -----
    def _maybe_autoprestige(self):
        if self._eval_policy(self.ap_policy):
            self.prestige()

    def _eval_policy(self, policy: str) -> bool:
        # Supported vars: steps, family, coh, insight, tier; ops: >=, <=, >, <, ==; bool ops: AND, OR
        # Example: "steps>=4 OR family<=2"
        expr = policy.upper().replace("AND"," and ").replace("OR"," or ")
        vals = {
            "STEPS": self._steps(),
            "FAMILY": len(self.family),
            "COH": self.coh,
            "INSIGHT": self.insight,
            "TIER": self.tier,
        }
        # safe eval: replace var names with ints; only digits, ops, spaces, and/or allowed
        for k,v in vals.items():
            expr = re_safe_replace(expr, k, str(v))
        if not is_safe_policy(expr):
            return False
        try:
            return bool(eval(expr, {"__builtins__": {}}, {}))
        except Exception:
            return False

    # ----- save/load -----
    def to_dict(self) -> Dict:
        return {
            "coh": self.coh, "insight": self.insight, "tier": self.tier,
            "speed": self.speed, "auto_rate": self.auto_rate, "buff_mult": self.buff_mult,
            "costs": {"pre": self.cost_pre, "spd": self.cost_spd, "auto": self.cost_auto},
            "ap_policy": self.ap_policy, "mode": self.mode,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "equipped": self.artifacts.index(self.equipped) if self.equipped in self.artifacts else None,
            "axiom_flags": self.axiom_flags,
            "challenge_start": self.challenge_start,
        }

    def save(self) -> str:
        with open(SAVEFILE, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        return SAVEFILE

    def load(self) -> bool:
        if not os.path.exists(SAVEFILE):
            return False
        with open(SAVEFILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        self.coh = d.get("coh",0); self.insight = d.get("insight",0); self.tier = d.get("tier",1)
        self.speed = d.get("speed",1); self.auto_rate = d.get("auto_rate",0.0); self.buff_mult = d.get("buff_mult",1.0)
        c = d.get("costs",{})
        self.cost_pre = c.get("pre",10); self.cost_spd = c.get("spd",15); self.cost_auto = c.get("auto",25)
        self.ap_policy = d.get("ap_policy","steps>=4 OR family<=2")
        self.mode = d.get("mode","forward")
        self.artifacts = [Artifact.from_dict(x) for x in d.get("artifacts",[])]
        eq = d.get("equipped")
        self.equipped = self.artifacts[eq] if isinstance(eq,int) and 0 <= eq < len(self.artifacts) else None
        self.axiom_flags.update(d.get("axiom_flags",{}))
        self.challenge_start = d.get("challenge_start", time.time())
        return True

    # ----- DOT visualizer -----
    def dump_dot(self, path: str) -> str:
        sizes = self._tower_sizes()
        with open(path, "w", encoding="utf-8") as f:
            f.write("digraph Tower {\n")
            f.write("  rankdir=LR;\n")
            for i, s in enumerate(sizes):
                f.write(f'  n{i} [label="H{i}\\n|H{i}|={s}"];\n')
            for i in range(len(sizes)-1):
                f.write(f"  n{i} -> n{i+1};\n")
            f.write("}\n")
        return path

# --- small helpers for safe policy parsing ---
import re as _re
def re_safe_replace(expr: str, name: str, value: str) -> str:
    return _re.sub(rf'\b{name}\b', value, expr)

def is_safe_policy(expr: str) -> bool:
    # Only allow digits, spaces, parentheses, comparison ops, and/or/not, arithmetic +-
    return bool(_re.fullmatch(r"[0-9\s\(\)><=!\-&|orandt]+", expr))

# ---------- CLI ----------
HELP = """
Commands:
  status                          Show status (process offline first)
  tick                            Apply nuclei (speed times)
  run N                           Run N ticks
  buy preorder|speed|auto         Purchase upgrades (cost: coherence)
  prestige                        Reset; gain insight; +5% permanent buff
  autopolicy EXPR                 Set auto-prestige policy (e.g., steps>=5 OR family<=2)
  autoprestige                    Run policy check immediately
  artifacts                       List artifacts
  equip I                         Equip artifact index I
  axiom FORMULA                   Spend 5 insight; if holds, +5% buff
  pack NAME                       Spend 15 insight; if holds (S4/S5), +10% buff + unique artifact
  mode forward|backward           Set modality used by modal checks
  challenges                      List challenge status
  dumpdot FILE.dot                Write DOT graph of tower sizes
  save | load                     Save / load game state
  help                            Show commands
  quit                            Exit
"""

def main():
    g = Game(n=5)
    print("RITM Idle v3 — subsets print money. Type 'help'.")
    while True:
        try:
            cmd = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye."); break

        ticks, base = g.process_offline()
        if ticks > 0:
            print(f"[offline] {ticks} ticks, base {base}, coh {g.coh}")

        if not cmd:
            continue
        parts = cmd.split()
        op = parts[0].lower()

        if op == "help":
            print(HELP)

        elif op == "status":
            steps = g._steps()
            sizes = g._tower_sizes()
            eq = f"{g.equipped.name} x{g.equipped.mult:.2f}" if g.equipped else "none"
            print(
                f"U={len(g.U.U)} family={len(g.family)} nuclei={len(g.nuclei)} steps={steps}\n"
                f"tower sizes: {sizes}\n"
                f"coh={g.coh} insight={g.insight} tier={g.tier} buff={g.buff_mult:.2f}\n"
                f"speed={g.speed} auto={g.auto_rate}/s policy='{g.ap_policy}'\n"
                f"costs: preorder={g.cost_pre} speed={g.cost_spd} auto={g.cost_auto}\n"
                f"equipped: {eq}\n"
                f"axioms: {g.axiom_flags}"
            )

        elif op == "tick":
            base, st = g.tick()
            print(f"tick: base +{base}, coh {g.coh}, family {len(g.family)}")
            if st: print("stabilized.")

        elif op == "run":
            if len(parts) < 2 or not parts[1].isdigit():
                print("usage: run N"); continue
            N = int(parts[1]); tot = 0
            for _ in range(N): b,_ = g.tick(); tot += b
            print(f"ran {N} ticks: base {tot}, coh {g.coh}, family {len(g.family)}")

        elif op == "buy":
            if len(parts) < 2: print("buy what? preorder|speed|auto"); continue
            what = parts[1].lower()
            ok = False
            if what == "preorder": ok = g.buy_preorder()
            elif what == "speed":  ok = g.buy_speed()
            elif what == "auto":   ok = g.buy_auto()
            print("bought" if ok else "not enough coherence")

        elif op == "prestige":
            earn = g.prestige()
            print(f"prestige +{earn} insight, tier {g.tier}, buff {g.buff_mult:.2f}")

        elif op == "autopolicy":
            expr = cmd[len("autopolicy"):].strip()
            if not expr:
                print(f"current policy: {g.ap_policy}")
            else:
                g.ap_policy = expr
                print("policy set to:", g.ap_policy)

        elif op == "autoprestige":
            g._maybe_autoprestige()
            print("policy evaluated. coh", g.coh, "insight", g.insight, "tier", g.tier)

        elif op == "artifacts":
            if not g.artifacts: print("no artifacts")
            for i,a in enumerate(g.artifacts):
                mark = "(equipped)" if g.equipped is a else ""
                print(f"[{i}] {a.name} | steps {a.steps} | x{a.mult:.2f} | {a.tag} {mark}")

        elif op == "equip":
            if len(parts) < 2 or not parts[1].isdigit():
                print("usage: equip I"); continue
            i = int(parts[1])
            print("equipped" if g.equip(i) else "invalid index")

        elif op == "axiom":
            formula = cmd[len("axiom"):].strip()
            if not formula:
                print("usage: axiom FORMULA"); continue
            ok,msg = g.assert_axiom(formula, cost=5)
            print(("OK: " if ok else "Nope: ") + msg)

        elif op == "pack":
            if len(parts) < 2:
                print("usage: pack NAME (e.g., S4 or S5)"); continue
            ok,msg = g.prove_pack(parts[1], cost=15)
            print(("OK: " if ok else "Nope: ") + msg)

        elif op == "mode":
            if len(parts) < 2:
                print("usage: mode forward|backward"); continue
            g.mode = parts[1]
            print("mode set to", g.mode)

        elif op == "challenges":
            for c in g.challenges:
                print(f"[{'✓' if c.done else '…'}] {c.name}: {c.desc}  (+{c.reward} insight)")

        elif op == "dumpdot":
            if len(parts) < 2:
                print("usage: dumpdot FILE.dot"); continue
            path = os.path.join(HERE, parts[1])
            out = g.dump_dot(path)
            print("Wrote", out)

        elif op == "save":
            path = g.save(); print("saved to", path)

        elif op == "load":
            ok = g.load(); print("loaded" if ok else "no save found")

        elif op == "quit":
            print("bye."); break

        else:
            print("unknown; try 'help'")

if __name__ == "__main__":
    main()
