/-
Regenerate the MetroPlat fixture with:
  lake env lean --run scripts/emit-golden-vectors.lean > ../../apps/metroplat/test/fixtures/lean-golden-vectors-2026-07-10.jsonl
-/

import Obsmetrologia.Site.Section

namespace Obsmetrologia.GoldenVectors

open Obsmetrologia

def charges : List Charge := [Charge.kBot, Charge.tTop, Charge.tBot, Charge.kTop]

def chargeName : Charge → String
  | Articulating.Corner.potential => "unknown"
  | Articulating.Corner.active => "held"
  | Articulating.Corner.stable => "denied"
  | Articulating.Corner.absurd => "contested"

def row (entity action : String) (value : Lean.Json) (time : String) : Lean.Json :=
  Lean.Json.mkObj [
    ("$schema", Lean.Json.str "metroplat/conformance/golden-vector"),
    ("e", Lean.Json.str entity),
    ("a", Lean.Json.str action),
    ("v", value),
    ("t", Lean.Json.str time),
  ]

def joinRows : List Lean.Json :=
  charges.flatMap fun left => charges.map fun right =>
    row (chargeName left) "joinKnowledgeValue" (Lean.Json.str (chargeName (Charge.joinK left right))) (chargeName right)

def maskRows (name : String) (mask : AssocSheaf.Mask) : List Lean.Json :=
  charges.map fun charge =>
    let valuation : Valuation := fun _ => charge
    let cell : PredicationCell := Inhabited.default
    row "cell-0" name (Lean.Json.bool (mask valuation cell)) (chargeName charge)

def vectors : List Lean.Json :=
  joinRows ++ maskRows "dT" AssocSheaf.dT ++ maskRows "dTop" AssocSheaf.dTop ++ maskRows "dK" AssocSheaf.dK

def main : IO Unit := vectors.forM fun vector => IO.println vector.compress

end Obsmetrologia.GoldenVectors

def main : IO Unit := Obsmetrologia.GoldenVectors.main
