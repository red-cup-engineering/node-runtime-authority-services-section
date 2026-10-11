"""
mud_relational.py — Unified single-player relational MUD
Every entity and action is a RelationalCell or a morphism between them.
"""

from cell import RelationalCell
from cell_laws import RC, RT, box, diamond, delta
from analysis import coherence_index, summary

# -------------------------------------------------------------------------
# --- World and entities --------------------------------------------------
# -------------------------------------------------------------------------

class WorldCell(RelationalCell):
    """Ambient cell that holds and updates all sub-cells."""
    def __init__(self):
        super().__init__()
        self.cells = {}  # name -> subcell (players, npcs, items)

    def register(self, name: str, cell: RelationalCell):
        self.cells[name] = cell

    def step(self):
        """Advance world one tick — apply a modal evolution."""
        evt = box(self.Y) or diamond(self.Y) or delta(self.Y)
        if evt:
            i, j = evt
            self.Y.setdefault(i, set()).add(j)

class PlayerCell(RelationalCell):
    """A self-aware cell that perceives and acts."""
    def __init__(self, name: str, start_node):
        super().__init__()
        self.name = name
        self.position = start_node
        self.knowledge = RelationalCell()
        self.inventory = []

    # --- Morphisms -------------------------------------------------------
    def perceive(self, world: WorldCell):
        """Functorial morphism: world → player. Merge visible Y,R."""
        for j in world.Y.get(self.position, set()):
            self.knowledge.Y.setdefault(self.position, set()).add(j)
        for j in world.R.get(self.position, set()):
            self.knowledge.R.setdefault(self.position, set()).add(j)

    def act(self, world: WorldCell, target):
        """player → world morphism: try to move along Y edge."""
        if target in world.Y.get(self.position, ()):
            self.position = target
            self.knowledge.Y.setdefault(self.position, set())
            return True
        return False

    def coherence(self) -> float:
        return coherence_index(self.knowledge)


class ItemCell(RelationalCell):
    """Passive relational object (artifact, key, etc.)."""
    def __init__(self, name: str, at_node):
        super().__init__()
        self.name = name
        self.position = at_node


# -------------------------------------------------------------------------
# --- Utility: morphisms -------------------------------------------------
# -------------------------------------------------------------------------

def perceive(player: PlayerCell, world: WorldCell):
    player.perceive(world)
    print(f"{player.name} perceives environment. "
          f"Coherence now {player.coherence():.3f}")

def move(player: PlayerCell, world: WorldCell, target):
    if player.act(world, target):
        print(f"{player.name} moves to {target}.")
    else:
        print("No relational path that way.")

def talk(a: PlayerCell, b: PlayerCell):
    """Mutual RT coupling between two cells."""
    evt = RT(a.Y, {a.position, b.position})
    if evt:
        print(f"{a.name} and {b.name} exchange relation {evt}.")
        a.R.setdefault(a.position, set()).add(b.position)
        b.R.setdefault(b.position, set()).add(a.position)

def merge(a: RelationalCell, b: RelationalCell):
    """Union morphism: merge two cells into a composite."""
    merged = RelationalCell()
    merged.Y = {**a.Y}
    for i, js in b.Y.items():
        merged.Y.setdefault(i, set()).update(js)
    merged.R = {**a.R}
    for i, js in b.R.items():
        merged.R.setdefault(i, set()).update(js)
    return merged


# -------------------------------------------------------------------------
# --- Minimal playable shell ----------------------------------------------
# -------------------------------------------------------------------------

def build_world() -> WorldCell:
    world = WorldCell()
    world.Y = {
        (0,0): {(1,0)},
        (1,0): {(0,0), (2,0)},
        (2,0): {(1,0)}
    }
    world.R = {(0,0): {(1,0)}, (1,0): {(0,0),(2,0)}, (2,0): {(1,0)}}
    return world

ROOM_NAMES = {(0,0): "Foyer", (1,0): "Hallway", (2,0): "Library"}

def describe(world, pos):
    name = ROOM_NAMES.get(pos, str(pos))
    exits = [ROOM_NAMES.get(j,str(j)) for j in world.Y.get(pos,())]
    return f"{name}. Exits: {', '.join(exits) or 'none'}"

def main():
    world = build_world()
    player = PlayerCell("You", (0,0))
    world.register("you", player)
    print("Welcome to the Relational-MUD.\n"
          "Commands: look, move <id>, talk, summary, quit.\n")

    while True:
        cmd = input("> ").strip().split()
        if not cmd: continue
        verb, *args = cmd

        if verb in ("look","l"):
            perceive(player, world)
            print(describe(world, player.position))

        elif verb in ("move","go"):
            if not args:
                print("Move where? Available:", world.Y.get(player.position))
                continue
            # match by number or neighbor id
            try:
                target = (int(args[0]), 0)
            except ValueError:
                # attempt to find by name
                target = next((p for p,n in ROOM_NAMES.items()
                               if n.lower()==args[0].lower()), None)
            move(player, world, target)

        elif verb == "talk":
            npc = PlayerCell("Echo", player.position)
            talk(player, npc)

        elif verb == "summary":
            print(summary(world))
            print(f"Your internal coherence: {player.coherence():.3f}")

        elif verb in ("quit","exit"):
            print("Exiting world.")
            break

        else:
            print("Unknown command.")

if __name__ == "__main__":
    main()
