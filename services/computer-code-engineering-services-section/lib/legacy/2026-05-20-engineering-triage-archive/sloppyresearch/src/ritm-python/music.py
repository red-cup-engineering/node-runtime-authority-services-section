#!/usr/bin/env python3
"""
ritm_live_minimal.py — hear the Relational ∞-Topos without MIDI or extra libs.
Requires only numpy and a system audio player (aplay, ffplay, or afplay).
"""

import math, os, io, wave, random, subprocess
import numpy as np
from cell import RelationalCell
from analysis import normalized_entropy, relational_curvature, coherence_index, nodes_edges_from


def scale_pitch(nid, lvl, key_pc=0, scale=[0,2,3,5,7,10]):
    degree = nid % len(scale)
    octave = 4 + (lvl % 3)
    pc = (scale[degree] + key_pc) % 12
    midi = 12 * (octave + 1) + pc
    return 440.0 * (2 ** ((midi - 69) / 12))  # Hz


def motif_from_cell(cell, base_dur=0.4, base_amp=0.2):
    nodes, edges = nodes_edges_from(cell)
    curv = relational_curvature(cell)
    order = sorted(nodes)
    motif = []
    for n in order:
        pid, lvl = n
        freq = scale_pitch(pid, lvl)
        amp = base_amp * (1.0 + 0.8 * abs(curv.get(n, 0.0)))
        outdeg = sum(1 for (i,j) in edges if i == n)
        dur = base_dur * (1.6 if outdeg <= 1 else 1.0 if outdeg == 2 else 0.6)
        motif.append((freq, dur, amp))
    return motif


def sine_wave(freq, dur, amp, sr):
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    env = np.minimum(1.0, np.concatenate([
        np.linspace(0,1,int(sr*0.02)),
        np.ones(max(1,int(sr*(dur-0.04)))),
        np.linspace(1,0,int(sr*0.02))
    ])[:len(t)])
    return (amp * np.sin(2*np.pi*freq*t) * env).astype(np.float32)


def render_audio(motif, tempo=100, sr=44100):
    seconds_per_beat = 60.0 / tempo
    pieces = [sine_wave(f, d * seconds_per_beat, a, sr) for f,d,a in motif]
    return np.concatenate(pieces)


def play_audio(data, sr=44100):
    """Write data to a temporary WAV and stream to system player."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes((data * 32767).astype(np.int16).tobytes())
    tmp = '/tmp/ritm_live.wav'
    with open(tmp, 'wb') as f: f.write(buf.getvalue())

    # Choose a system player
    if os.system('which aplay > /dev/null 2>&1') == 0:
        subprocess.run(['aplay', tmp])
    elif os.system('which ffplay > /dev/null 2>&1') == 0:
        subprocess.run(['ffplay', '-nodisp', '-autoexit', tmp])
    elif os.system('which afplay > /dev/null 2>&1') == 0:
        subprocess.run(['afplay', tmp])
    else:
        print(f"No system audio player found; file written to {tmp}")


def main():
    random.seed(42)
    cell = RelationalCell(0, 1)
    cell.run(steps=24)
    tempo = int(96 + 48*(normalized_entropy(cell)-0.5)
                + 24*(coherence_index(cell)-0.5))
    motif = motif_from_cell(cell)
    print(f"Rendering {len(motif)} notes at {tempo} bpm …")
    audio = render_audio(motif, tempo)
    play_audio(audio)


if __name__ == "__main__":
    main()
