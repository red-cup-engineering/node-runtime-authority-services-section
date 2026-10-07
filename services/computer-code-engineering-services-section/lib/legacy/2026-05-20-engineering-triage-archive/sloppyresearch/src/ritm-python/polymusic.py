#!/usr/bin/env python3
"""
ritm_duet.py — two-voice live performance from Relational ∞-Topos dynamics.

Uses only the existing RITM modules:
    cell.py
    analysis.py
and requires pygame for real-time MIDI playback.

Voice A (motif): walks the Y relation, with curvature modulating velocity.
Voice B (harmony): derives light arpeggiated chords from R relations.
"""

import math, random, time
from cell import RelationalCell
from analysis import normalized_entropy, relational_curvature, coherence_index, nodes_edges_from

# external dependency (install once: pip install pygame)
import pygame.midi as midi

# --------------------- music helpers ---------------------

def scale_pitch(nid, lvl, key_pc=0, scale=[0,2,3,5,7,10]):
    """Map a node ID and level to a MIDI pitch in a pentatonic-minor scale."""
    degree = nid % len(scale)
    octave = 4 + (lvl % 3)
    pc = (scale[degree] + key_pc) % 12
    return 12 * (octave + 1) + pc

def motif_from_Y(cell, base_dur=0.5, base_vel=90, key_pc=0):
    """Melodic voice from Y relation."""
    nodes, edges = nodes_edges_from(cell)
    curv = relational_curvature(cell)
    order = sorted(nodes)
    notes = []
    for (pid, lvl) in order:
        pitch = scale_pitch(pid, lvl, key_pc)
        vel = max(20, min(120, int(base_vel * (1.0 + 0.5 * abs(curv.get((pid,lvl), 0.0))))))
        outdeg = sum(1 for (i,j) in edges if i == (pid,lvl))
        dur = base_dur * (1.5 if outdeg <= 1 else 1.0 if outdeg == 2 else 0.5)
        notes.append((pitch, dur, vel))
    return notes

def harmony_from_R(cell, base_dur=0.25, base_vel=70, key_pc=0):
    """Simple arpeggiated harmony from R relations."""
    chords = []
    for i, row in cell.R.items():
        pcs = [scale_pitch(j[0], j[1], key_pc) for j in sorted(row)]
        if pcs:
            for p in sorted(pcs):
                chords.append((p, base_dur, base_vel))
    return chords

# --------------------- main music logic ---------------------

def main():
    print("Initializing RelationalCell ...")
    cell = RelationalCell(0, 1)
    cell.run(steps=30)

    print("Analyzing field ...")
    tempo = int(96 + 48*(normalized_entropy(cell)-0.5) + 24*(coherence_index(cell)-0.5))
    motif = motif_from_Y(cell)
    harmony = harmony_from_R(cell)
    print(f"Tempo ≈ {tempo} bpm, motif={len(motif)} notes, harmony={len(harmony)} notes")

    # Initialize MIDI output
    midi.init()
    out_id = midi.get_default_output_id()
    player = midi.Output(out_id)
    player.set_instrument(0, 0)  # Piano (Motif)
    player.set_instrument(48, 1) # Strings Ensemble (Harmony)

    qn_time = 60.0 / tempo  # seconds per quarter note

    print("Performing live duet ... (Ctrl+C to stop)")
    try:
        # play voices interleaved: motif on ch 0, harmony on ch 1
        iA = iB = 0
        tA = tB = 0.0
        start = time.time()
        while iA < len(motif) or iB < len(harmony):
            now = time.time() - start
            # play motif note if time
            if iA < len(motif) and now >= tA:
                pitch, dur, vel = motif[iA]
                player.note_on(pitch, vel, 0)
                player.note_off(pitch, vel, int(dur * 480))
                tA += dur * qn_time
                iA += 1
            # play harmony note if time
            if iB < len(harmony) and now >= tB:
                pitch, dur, vel = harmony[iB]
                player.note_on(pitch, vel, 1)
                player.note_off(pitch, vel, int(dur * 480))
                tB += dur * qn_time * 0.75  # offset slightly
                iB += 1
            time.sleep(0.01)
        print("Done.")
    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        player.close()
        midi.quit()

if __name__ == "__main__":
    main()
