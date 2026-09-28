"""
Synthesises every Cinderbound sound effect and music loop from scratch
(no samples, no third-party audio). Output:
  assets/audio/sfx/*.wav     assets/audio/music/*.ogg (via ffmpeg/libvorbis)
Run: python3 tools/make_audio.py
"""
import os
import subprocess
import wave
import numpy as np

SR = 32000
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
rng = np.random.default_rng(7)


def t_axis(dur):
    return np.arange(int(SR * dur)) / SR


def env(n, a=0.005, d=0.1, s=0.6, r=0.1, dur=None):
    """ADSR envelope of n samples."""
    total = n / SR
    a_n, d_n, r_n = int(a * SR), int(d * SR), int(r * SR)
    s_n = max(n - a_n - d_n - r_n, 0)
    e = np.concatenate([np.linspace(0, 1, max(a_n, 1)), np.linspace(1, s, max(d_n, 1)),
                        np.full(s_n, s), np.linspace(s, 0, max(r_n, 1))])
    return e[:n] if len(e) >= n else np.pad(e, (0, n - len(e)))


def square(freq, dur, duty=0.5, sweep_to=None):
    t = t_axis(dur)
    f = freq if sweep_to is None else np.linspace(freq, sweep_to, len(t))
    phase = np.cumsum(np.full(len(t), f) / SR) if np.isscalar(f) else np.cumsum(f / SR)
    return np.where((phase % 1.0) < duty, 1.0, -1.0)


def tri(freq, dur, sweep_to=None):
    t = t_axis(dur)
    f = np.full(len(t), freq) if sweep_to is None else np.linspace(freq, sweep_to, len(t))
    phase = np.cumsum(f / SR) % 1.0
    return 4 * np.abs(phase - 0.5) - 1


def sine(freq, dur, sweep_to=None):
    t = t_axis(dur)
    f = np.full(len(t), freq) if sweep_to is None else np.linspace(freq, sweep_to, len(t))
    return np.sin(2 * np.pi * np.cumsum(f / SR))


def noise(dur):
    return rng.uniform(-1, 1, int(SR * dur))


def lowpass(x, cutoff):
    """Simple one-pole low-pass (cutoff may be an array)."""
    y = np.zeros_like(x)
    c = np.broadcast_to(cutoff, x.shape)
    a = 1 - np.exp(-2 * np.pi * c / SR)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def highpass(x, cutoff):
    return x - lowpass(x, cutoff)


def norm(x, peak=0.85):
    m = np.max(np.abs(x)) if len(x) else 1
    return x / m * peak if m > 0 else x


def write_wav(path, x):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def mix(*parts):
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[:len(p)] += p
    return out


# ------------------------------------------------------------------ SFX
def sfx_click():
    x = square(1400, 0.04, 0.25) * env(int(SR * 0.04), 0.001, 0.02, 0.3, 0.015)
    return norm(x, 0.5)


def sfx_hover():
    x = sine(900, 0.025) * env(int(SR * 0.025), 0.001, 0.01, 0.3, 0.01)
    return norm(x, 0.3)


def sfx_sword():
    n = noise(0.22)
    cut = np.linspace(6000, 900, len(n))
    whoosh = highpass(lowpass(n, cut), 500) * env(len(n), 0.01, 0.08, 0.3, 0.1)
    ring = (sine(2300, 0.22) * 0.4 + sine(3450, 0.22) * 0.2) * np.exp(-t_axis(0.22) * 22)
    return norm(mix(whoosh * 1.4, ring), 0.8)


def sfx_hit():
    thump = sine(150, 0.14, 55) * np.exp(-t_axis(0.14) * 25)
    crack = lowpass(noise(0.08), 3000) * np.exp(-t_axis(0.08) * 50)
    return norm(mix(thump, crack * 0.8), 0.85)


def sfx_water():
    t = t_axis(0.35)
    f = 500 + 250 * np.sin(2 * np.pi * 18 * t) + np.linspace(0, 300, len(t))
    bub = np.sin(2 * np.pi * np.cumsum(f / SR)) * env(len(t), 0.01, 0.1, 0.5, 0.15)
    hiss = lowpass(noise(0.35), 2500) * env(len(t), 0.05, 0.1, 0.3, 0.15) * 0.4
    return norm(mix(bub, hiss), 0.7)


def sfx_water_hit():
    n = lowpass(noise(0.25), np.linspace(4000, 600, int(SR * 0.25)))
    drop = sine(900, 0.12, 300) * np.exp(-t_axis(0.12) * 30)
    return norm(mix(n * np.exp(-t_axis(0.25) * 14), drop * 0.6), 0.8)


def sfx_nature():
    thunk = tri(220, 0.18, 90) * np.exp(-t_axis(0.18) * 18)
    crackle = np.zeros(int(SR * 0.18))
    for k in range(6):
        i = rng.integers(0, len(crackle) - 200)
        crackle[i:i + 200] += noise(200 / SR) * np.exp(-np.arange(200) / 40)
    return norm(mix(thunk, crackle * 0.5), 0.85)


def sfx_fire():
    n = lowpass(noise(0.35), 1800) * env(int(SR * 0.35), 0.02, 0.1, 0.5, 0.2)
    pops = np.zeros(int(SR * 0.35))
    for k in range(10):
        i = rng.integers(0, len(pops) - 100)
        pops[i:i + 100] += rng.uniform(-1, 1, 100) * np.exp(-np.arange(100) / 15)
    return norm(mix(n, pops * 0.6), 0.8)


def sfx_burst():
    rise = square(180, 0.6, 0.3, sweep_to=1300) * env(int(SR * 0.6), 0.05, 0.2, 0.6, 0.25) * 0.5
    swell = lowpass(noise(0.6), np.linspace(400, 6000, int(SR * 0.6))) * np.linspace(0, 1, int(SR * 0.6)) ** 2
    boom = sine(90, 0.4, 40) * np.exp(-t_axis(0.4) * 8)
    return norm(mix(rise, swell * 0.7, np.concatenate([np.zeros(int(SR * 0.5)), boom])), 0.85)


def arp(notes, step, dur_each, wave_fn=sine, decay=10):
    out = np.zeros(int(SR * (step * len(notes) + dur_each)))
    for i, f in enumerate(notes):
        s = wave_fn(f, dur_each) * np.exp(-t_axis(dur_each) * decay)
        a = int(i * step * SR)
        out[a:a + len(s)] += s
    return out


def sfx_heal():
    return norm(arp([523, 659, 784, 1047], 0.07, 0.3), 0.6)


def sfx_guard():
    t = t_axis(0.25)
    clank = (sine(1500, 0.25) + 0.6 * sine(2210, 0.25) + 0.3 * sine(3100, 0.25)) * np.exp(-t * 20)
    return norm(mix(clank, lowpass(noise(0.05), 5000) * 0.5), 0.6)


def sfx_ko():
    return norm(square(420, 0.4, 0.5, sweep_to=90) * env(int(SR * 0.4), 0.005, 0.1, 0.6, 0.2), 0.5)


def sfx_enemy_die():
    poof = lowpass(noise(0.35), np.linspace(3000, 300, int(SR * 0.35))) * np.exp(-t_axis(0.35) * 9)
    down = square(600, 0.25, 0.25, sweep_to=120) * np.exp(-t_axis(0.25) * 10) * 0.4
    return norm(mix(poof, down), 0.75)


def sfx_level_up():
    notes = [523, 659, 784, 1047, 1319]
    a = arp(notes, 0.06, 0.25, lambda f, d: square(f, d, 0.25), decay=9)
    sparkle = arp([2093, 2637, 3136], 0.05, 0.2, sine, decay=16)
    return norm(mix(a, np.concatenate([np.zeros(int(SR * 0.3)), sparkle * 0.4])), 0.6)


SFX = {'click': sfx_click, 'hover': sfx_hover, 'sword': sfx_sword, 'hit': sfx_hit, 'water': sfx_water,
       'water_hit': sfx_water_hit, 'nature': sfx_nature, 'fire': sfx_fire, 'burst': sfx_burst,
       'heal': sfx_heal, 'guard': sfx_guard, 'ko': sfx_ko, 'enemy_die': sfx_enemy_die, 'level_up': sfx_level_up}


# ---- UI / presentation cues (short, quiet)
def sfx_menu_open():
    x = mix(sine(520, 0.12, 780) * env(int(SR * 0.12), 0.005, 0.05, 0.4, 0.05),
            lowpass(noise(0.1), 3000) * np.exp(-t_axis(0.1) * 30) * 0.25)
    return norm(x, 0.45)


def sfx_menu_close():
    return norm(sine(700, 0.1, 420) * env(int(SR * 0.1), 0.003, 0.04, 0.3, 0.05), 0.4)


def sfx_unit_select():
    return norm(arp([660, 990], 0.045, 0.12, lambda f, d: square(f, d, 0.25), decay=22), 0.4)


def sfx_stage_select():
    thud = tri(200, 0.12, 140) * np.exp(-t_axis(0.12) * 24)
    chime = sine(1320, 0.18) * np.exp(-t_axis(0.18) * 18) * 0.5
    return norm(mix(thud, chime), 0.5)


def sfx_target():
    return norm(sine(1760, 0.06, 1400) * env(int(SR * 0.06), 0.002, 0.02, 0.3, 0.03), 0.3)


def sfx_reward():
    coin = mix(square(1568, 0.08, 0.25) * np.exp(-t_axis(0.08) * 30),
               np.concatenate([np.zeros(int(SR * 0.05)), square(2093, 0.14, 0.25) * np.exp(-t_axis(0.14) * 20)]))
    return norm(coin, 0.45)


def sfx_burst_ready():
    shimmer = arp([784, 1175, 1568, 2349], 0.035, 0.22, sine, decay=12)
    return norm(mix(shimmer, lowpass(noise(0.3), 6000) * np.exp(-t_axis(0.3) * 12) * 0.15), 0.5)


def sfx_boss_sting():
    boom = sine(55, 1.1, 38) * np.exp(-t_axis(1.1) * 3)
    growl = lowpass(noise(1.1), 400) * env(int(SR * 1.1), 0.2, 0.3, 0.6, 0.5) * 0.6
    stab = mix(square(110, 0.9, 0.5), square(116.5, 0.9, 0.5), square(164.8, 0.9, 0.5)) * env(int(SR * 0.9), 0.01, 0.3, 0.5, 0.4) * 0.3
    return norm(mix(boom, growl, stab), 0.9)


def sfx_impact():
    thump = sine(80, 0.3, 35) * np.exp(-t_axis(0.3) * 10)
    crack = lowpass(noise(0.15), 5000) * np.exp(-t_axis(0.15) * 25)
    return norm(mix(thump * 1.2, crack), 0.9)


SFX.update({'menu_open': sfx_menu_open, 'menu_close': sfx_menu_close, 'unit_select': sfx_unit_select,
            'stage_select': sfx_stage_select, 'target': sfx_target, 'reward': sfx_reward,
            'burst_ready': sfx_burst_ready, 'boss_sting': sfx_boss_sting, 'impact': sfx_impact})


# ---- summon / progression cues (World 2 update)
def seeded(seed):
    """Run a generator with its own noise stream, so adding or regenerating it
    (e.g. with --only) never shifts the random sequence of any other sound."""
    def deco(fn):
        def wrapped():
            global rng
            saved = rng
            rng = np.random.default_rng(seed)
            try:
                return fn()
            finally:
                rng = saved
        wrapped.__name__ = fn.__name__
        return wrapped
    return deco


def bell(freq, dur, decay=6.0):
    """Struck-bell tone: inharmonic partials that fade at different rates."""
    t = t_axis(dur)
    out = np.zeros(len(t))
    for ratio, amp, dk in [(1.0, 1.0, 1.0), (2.0, 0.45, 1.6), (2.76, 0.35, 2.2), (5.4, 0.18, 3.5)]:
        out += amp * np.sin(2 * np.pi * freq * ratio * t) * np.exp(-t * decay * dk)
    return out * np.clip(t * 400, 0, 1)


def fade_tail(x, ms=40):
    n = min(len(x), int(SR * ms / 1000))
    x = x.copy()
    x[-n:] *= np.linspace(1, 0, n)
    return x


@seeded(101)
def sfx_summon_charge():
    dur = 0.95
    t = t_axis(dur)
    f = 260 * (4.5 ** (t / dur)) * (1 + 0.012 * np.sin(2 * np.pi * 7 * t))
    tone = np.sin(2 * np.pi * np.cumsum(f / SR)) + 0.35 * np.sin(2 * np.pi * np.cumsum(f * 1.5 / SR))
    swell = (t / dur) ** 2.2
    air = lowpass(noise(dur), np.linspace(500, 7000, len(t))) * swell * 0.5
    sparks = arp([784, 988, 1175, 1568, 1976, 2349], 0.12, 0.22, sine, decay=14) * 0.3
    x = mix(tone * swell * 0.7, air, np.concatenate([np.zeros(int(SR * 0.2)), sparks]))[:len(t)]
    return norm(fade_tail(x, 30), 0.7)


@seeded(102)
def sfx_summon_reveal():
    dur = 0.7
    burst = highpass(noise(dur), 1500) * np.exp(-t_axis(dur) * 16) * 0.8
    stab = mix(*[square(f, dur, 0.25) * 0.25 + sine(f * 2, dur) * 0.3 for f in (523, 659, 784)]) * env(int(SR * dur), 0.004, 0.12, 0.35, 0.35)
    sparkle = arp([1568, 2093, 2637, 3136], 0.035, 0.3, sine, decay=12) * 0.35
    thump = sine(140, 0.25, 60) * np.exp(-t_axis(0.25) * 14)
    return norm(fade_tail(mix(burst, lowpass(stab, 5000), sparkle, thump)[:int(SR * dur)]), 0.8)


@seeded(103)
def sfx_summon_rare():
    dur = 1.0
    boom = sine(70, dur, 42) * np.exp(-t_axis(dur) * 4.5)
    chord = mix(*[square(f, dur, 0.5) * 0.18 for f in (262, 392, 523, 659, 784)])
    chord = lowpass(chord, 3500) * env(int(SR * dur), 0.01, 0.25, 0.45, 0.4)
    chimes = np.zeros(int(SR * dur))
    for i, f in enumerate([1047, 1319, 1568, 2093, 2637]):
        b = bell(f, dur - 0.1 - i * 0.07, decay=5) * 0.4
        a = int(SR * (0.1 + i * 0.07))
        chimes[a:a + len(b)] += b
    shimmer = highpass(noise(dur), 5000) * np.exp(-t_axis(dur) * 5) * 0.2
    return norm(fade_tail(mix(boom * 0.9, chord, chimes, shimmer)), 0.85)


@seeded(104)
def sfx_evolve():
    dur = 1.0
    t = t_axis(dur)
    sweep = np.concatenate([np.linspace(300, 5000, int(SR * 0.55)), np.linspace(5000, 900, len(t) - int(SR * 0.55))])
    whoosh = lowpass(highpass(noise(dur), 250), sweep) * np.sin(np.pi * np.clip(t / 0.75, 0, 1)) * 0.9
    rise = sine(220, 0.5, 880) * np.linspace(0, 1, int(SR * 0.5)) * 0.35
    chord = np.zeros(len(t))
    for f in (440, 554, 659, 880):
        s = (sine(f, 0.55) + 0.3 * square(f, 0.55, 0.5)) * env(int(SR * 0.55), 0.02, 0.15, 0.6, 0.3)
        a = int(SR * 0.42)
        chord[a:a + len(s)] += lowpass(s, 4000) * 0.3
    return norm(fade_tail(mix(whoosh, rise, chord)), 0.8)


@seeded(105)
def sfx_rank_up():
    notes = [(392, 0.0, 0.1), (523, 0.1, 0.1), (659, 0.2, 0.1), (784, 0.3, 0.8)]
    out = np.zeros(int(SR * 1.15))
    for f, at, d in notes:
        s = (square(f, d, 0.35) * 0.5 + square(f * 1.003, d, 0.5) * 0.3) * env(int(SR * d), 0.004, 0.04, 0.8, min(0.25, d * 0.4))
        a = int(SR * at)
        out[a:a + len(s)] += lowpass(s, 4200)
    for f in (262, 330, 392):   # supporting chord under the held note
        s = square(f, 0.8, 0.5) * env(int(SR * 0.8), 0.01, 0.2, 0.5, 0.35) * 0.18
        a = int(SR * 0.3)
        out[a:a + len(s)] += lowpass(s, 2500)
    sparkle = arp([1568, 2093, 2637], 0.05, 0.25, sine, decay=12) * 0.2
    out[int(SR * 0.35):int(SR * 0.35) + len(sparkle)] += sparkle[:len(out) - int(SR * 0.35)]
    return norm(fade_tail(out), 0.65)


@seeded(106)
def sfx_claim():
    out = np.zeros(int(SR * 0.5))
    for f, at in [(1319, 0.0), (1976, 0.07)]:
        b = bell(f, 0.4, decay=9) * 0.6
        a = int(SR * at)
        out[a:a + len(b)] += b[:len(out) - a]
    out += mix(highpass(noise(0.12), 6000) * np.exp(-t_axis(0.12) * 35) * 0.15, np.zeros(len(out)))
    return norm(fade_tail(out), 0.5)


@seeded(107)
def sfx_warning():
    out = np.zeros(int(SR * 0.95))
    for f, at in [(294, 0.0), (208, 0.42)]:        # D4 then G#3: a falling tritone
        d = 0.4
        s = (square(f, d, 0.5) * 0.5 + square(f * 1.01, d, 0.3) * 0.35 + sine(f / 2, d) * 0.4)
        s = np.tanh(s * 1.8) * env(int(SR * d), 0.005, 0.05, 0.85, 0.12)
        a = int(SR * at)
        out[a:a + len(s)] += lowpass(s, 2200)
    rumble = lowpass(noise(0.95), 180) * env(int(SR * 0.95), 0.05, 0.2, 0.7, 0.3) * 1.2
    return norm(fade_tail(out + rumble), 0.6)


@seeded(108)
def sfx_energy():
    x = sine(1250, 0.07, 1600) * np.exp(-t_axis(0.07) * 55) + 0.3 * sine(2500, 0.07) * np.exp(-t_axis(0.07) * 80)
    return norm(x, 0.28)


# ---- Phase 5 UI cues (quiet, short, distinct from battle sounds)
def sfx_ui_back():
    return norm(tri(620, 0.07, 440) * env(int(SR * 0.07), 0.002, 0.03, 0.3, 0.03), 0.32)


def sfx_ui_confirm():
    return norm(arp([784, 1175], 0.04, 0.11, lambda f, d: square(f, d, 0.25), decay=24), 0.36)


def sfx_ui_error():
    x = square(196, 0.16, 0.4, 170) * env(int(SR * 0.16), 0.004, 0.05, 0.6, 0.06)
    return norm(lowpass(x, 1800), 0.38)


def sfx_coin():
    return norm(mix(square(1976, 0.05, 0.25) * np.exp(-t_axis(0.05) * 40),
                    np.concatenate([np.zeros(int(SR * 0.03)), square(2637, 0.08, 0.25) * np.exp(-t_axis(0.08) * 35)])), 0.3)


@seeded(109)
def sfx_mission():
    return norm(fade_tail(arp([659, 880, 1109, 1319], 0.05, 0.25, sine, decay=10)), 0.42)


SFX.update({'ui_back': sfx_ui_back, 'ui_confirm': sfx_ui_confirm, 'ui_error': sfx_ui_error, 'coin': sfx_coin,
            'mission': sfx_mission})


SFX.update({'summon_charge': sfx_summon_charge, 'summon_reveal': sfx_summon_reveal, 'summon_rare': sfx_summon_rare,
            'evolve': sfx_evolve, 'rank_up': sfx_rank_up, 'claim': sfx_claim, 'warning': sfx_warning,
            'energy': sfx_energy})


# ------------------------------------------------------------------ MUSIC
NOTE_INDEX = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}


def nf(name):
    """'A4' -> Hz"""
    n, o = name[:-1], int(name[-1])
    midi = 12 * (o + 1) + NOTE_INDEX[n]
    return 440.0 * 2 ** ((midi - 69) / 12)


def chord_notes(root, kind, octave):
    base = 12 * (octave + 1) + NOTE_INDEX[root]
    iv = {'maj': [0, 4, 7], 'min': [0, 3, 7], 'sus': [0, 5, 7]}[kind]
    return [440.0 * 2 ** ((base + i - 69) / 12) for i in iv]


class Song:
    def __init__(self, bpm, bars):
        self.bpm = bpm
        self.step = 60.0 / bpm / 4          # 16th note
        self.length = int(SR * self.step * 16 * bars)
        self.buf = np.zeros(self.length + SR * 2)

    def add(self, sig, at_step, vol):
        a = int(at_step * self.step * SR)
        if a >= len(self.buf):
            return
        sig = sig[:len(self.buf) - a]
        self.buf[a:a + len(sig)] += sig * vol

    def lead(self, pattern, vol=0.18, duty=0.25, start=0, vib=True):
        """pattern: list of (note|'-', steps)."""
        pos = start
        for note, steps in pattern:
            if note != '-':
                dur = steps * self.step
                f = nf(note)
                t = t_axis(dur * 0.95)
                if vib and dur > 0.25:
                    f = f * (1 + 0.006 * np.sin(2 * np.pi * 5.5 * t) * np.clip(t * 3, 0, 1))
                    phase = np.cumsum(f / SR)
                    s = np.where(phase % 1 < duty, 1.0, -1.0)
                else:
                    s = square(f, dur * 0.95, duty)
                s = s * env(len(s), 0.005, 0.08, 0.7, min(0.08, dur * 0.3))
                self.add(s, pos, vol)
            pos += steps
        return pos

    def bass(self, roots, steps_each, octave=2, vol=0.3, pattern=None):
        pos = 0
        pattern = pattern or [(0, 4), (0, 4), (0, 4), (0, 4)]
        while pos * self.step * SR < self.length:
            for r in roots:
                f0 = nf(r + str(octave))
                p = pos
                for (semi, st) in pattern:
                    f = f0 * 2 ** (semi / 12)
                    s = tri(f, st * self.step * 0.9) * env(int(SR * st * self.step * 0.9), 0.003, 0.05, 0.8, 0.03)
                    self.add(s, p, vol)
                    p += st
                pos += steps_each
                if pos * self.step * SR >= self.length:
                    break

    def pad(self, chords, steps_each, vol=0.06, octave=4):
        pos = 0
        while pos * self.step * SR < self.length:
            for (root, kind) in chords:
                dur = steps_each * self.step
                for f in chord_notes(root, kind, octave):
                    s = square(f, dur, 0.5) * env(int(SR * dur), 0.08, 0.2, 0.6, 0.2)
                    self.add(lowpass(s, 1800), pos, vol)
                pos += steps_each

    def arp(self, chords, steps_each, vol=0.07, octave=5, rate=2):
        pos = 0
        while pos * self.step * SR < self.length:
            for (root, kind) in chords:
                notes = chord_notes(root, kind, octave)
                for k in range(0, steps_each, rate):
                    f = notes[(k // rate) % 3]
                    s = square(f, rate * self.step * 0.8, 0.125) * env(int(SR * rate * self.step * 0.8), 0.002, 0.04, 0.4, 0.03)
                    self.add(s, pos + k, vol)
                pos += steps_each

    def drums(self, kick, snare, hat, vol=0.35, steps=16):
        """kick/snare/hat: strings of 16 chars ('x' = hit) repeated through the song."""
        total_steps = int(self.length / SR / self.step)
        for i in range(total_steps):
            k = i % steps
            if kick[k] == 'x':
                self.add(sine(110, 0.12, 45) * np.exp(-t_axis(0.12) * 22), i, vol)
            if snare[k] == 'x':
                sn = highpass(noise(0.12), 900) * np.exp(-t_axis(0.12) * 26)
                self.add(sn, i, vol * 0.55)
            if hat[k] == 'x':
                hh = highpass(noise(0.03), 5000) * np.exp(-t_axis(0.03) * 90)
                self.add(hh, i, vol * 0.3)

    def render(self, loop=True):
        out = self.buf[:self.length].copy()
        if loop:
            tail = self.buf[self.length:self.length + SR * 2]
            out[:len(tail)] += tail   # wrap release tails to the start for a seamless loop
        else:
            out = self.buf.copy()
            nz = np.nonzero(np.abs(out) > 1e-4)[0]
            out = out[:nz[-1] + 1] if len(nz) else out
        out = np.tanh(out * 1.2)
        return norm(out, 0.8)


def song_menu():
    s = Song(84, 16)
    ch = [('A', 'min'), ('F', 'maj'), ('C', 'maj'), ('G', 'maj')]
    s.pad(ch * 4, 16, vol=0.07)
    s.bass(['A', 'F', 'C', 'G'], 16, octave=2, vol=0.25, pattern=[(0, 8), (7, 8)])
    motif = [('E5', 6), ('D5', 2), ('C5', 4), ('A4', 4), ('F4', 6), ('G4', 2), ('A4', 8), ('-', 8),
             ('C5', 6), ('B4', 2), ('A4', 4), ('G4', 4), ('B4', 8), ('-', 4), ('D5', 4)]
    motif2 = [('E5', 4), ('G5', 4), ('A5', 8), ('F5', 6), ('E5', 2), ('C5', 8), ('E5', 4), ('D5', 4),
              ('C5', 4), ('D5', 4), ('B4', 12), ('-', 4)]
    pos = s.lead(motif, 0.13, 0.5)
    pos = s.lead(motif2, 0.13, 0.5, pos)
    pos = s.lead(motif, 0.13, 0.5, pos)
    s.lead(motif2[:-2] + [('A4', 16)], 0.13, 0.5, pos)
    s.arp(ch * 4, 16, vol=0.035, octave=5, rate=2)
    return s.render()


def song_world():
    s = Song(112, 16)
    ch = [('D', 'maj'), ('G', 'maj'), ('A', 'maj'), ('B', 'min'), ('G', 'maj'), ('D', 'maj'), ('E', 'min'), ('A', 'maj')]
    s.pad(ch * 2, 16, vol=0.05)
    s.bass([c[0] for c in ch], 16, vol=0.28, pattern=[(0, 4), (7, 2), (0, 2), (12, 4), (7, 4)])
    a = [('F#5', 4), ('A5', 4), ('D6', 6), ('C#6', 2), ('B5', 4), ('A5', 4), ('G5', 8),
         ('E5', 4), ('F#5', 4), ('A5', 8), ('B5', 4), ('A5', 2), ('F#5', 2), ('E5', 8)]
    b = [('D5', 4), ('E5', 4), ('F#5', 4), ('G5', 4), ('A5', 6), ('B5', 2), ('A5', 8),
         ('G5', 4), ('F#5', 4), ('E5', 4), ('C#5', 4), ('D5', 16)]
    pos = s.lead(a, 0.12)
    pos = s.lead(b, 0.12, 0.25, pos)
    pos = s.lead(a, 0.12, 0.25, pos)
    s.lead(b, 0.12, 0.25, pos)
    s.drums('x.......x.......', '....x.......x...', 'x.x.x.x.x.x.x.x.', vol=0.25)
    return s.render()


def song_battle():
    s = Song(150, 16)
    ch = [('E', 'min'), ('C', 'maj'), ('D', 'maj'), ('B', 'min')]
    s.bass([c[0] for c in ch] * 4, 16, octave=2, vol=0.32,
           pattern=[(0, 2), (0, 2), (12, 2), (0, 2), (0, 2), (10, 2), (12, 2), (7, 2)])
    s.arp(ch * 4, 16, vol=0.05, octave=4, rate=1)
    a = [('E5', 3), ('F#5', 1), ('G5', 4), ('B5', 4), ('A5', 4), ('G5', 2), ('F#5', 2), ('E5', 4), ('C5', 4), ('D5', 4),
         ('E5', 2), ('F#5', 2), ('D5', 4), ('B4', 8), ('-', 4)]
    b = [('B5', 4), ('A5', 2), ('G5', 2), ('A5', 4), ('F#5', 4), ('G5', 4), ('E5', 4), ('C6', 4), ('B5', 4),
         ('A5', 4), ('F#5', 4), ('D6', 4), ('B5', 12)]
    pos = 0
    for part in (a, b, a, b):
        pos = s.lead(part, 0.11, 0.25, pos)
    s.drums('x.....x...x.....', '....x.......x..x', 'x.xxx.x.x.xxx.x.', vol=0.32)
    return s.render()


def song_boss():
    s = Song(160, 16)
    ch = [('C', 'min'), ('G#', 'maj'), ('A#', 'maj'), ('G', 'maj')]
    s.bass([c[0] for c in ch] * 4, 16, octave=2, vol=0.34,
           pattern=[(0, 1), (0, 1), (12, 2), (0, 1), (0, 1), (12, 2), (0, 2), (3, 2), (5, 2), (6, 2)])
    s.pad(ch * 4, 16, vol=0.05, octave=3)
    a = [('C5', 2), ('D#5', 2), ('G5', 4), ('F#5', 2), ('G5', 2), ('G#5', 4), ('G5', 4), ('D#5', 4),
         ('F5', 4), ('D#5', 2), ('D5', 2), ('A#4', 8), ('G4', 4), ('B4', 4), ('D5', 8)]
    pos = 0
    for i in range(4):
        pos = s.lead(a if i % 2 == 0 else [(n if n == '-' else n[:-1] + str(int(n[-1]) + (1 if i == 3 else 0)), d) for n, d in a],
                     0.1, 0.5, pos)
    s.drums('x.x...x.x.x...x.', '....x.......x.xx', 'xxxxxxxxxxxxxxxx', vol=0.32)
    return s.render()


def song_victory():
    s = Song(140, 3)
    s.lead([('C5', 2), ('E5', 2), ('G5', 2), ('C6', 6), ('A#5', 3), ('C6', 3), ('D6', 2), ('E6', 12)], 0.18, 0.25)
    s.lead([('E4', 2), ('G4', 2), ('C5', 2), ('E5', 6), ('D5', 3), ('E5', 3), ('F5', 2), ('G5', 12)], 0.08, 0.5)
    for i, f in enumerate([nf('C3'), nf('C3'), nf('A#2'), nf('C3')]):
        s.add(tri(f, 0.5) * env(int(SR * 0.5), 0.01, 0.1, 0.8, 0.1), [0, 6, 12, 20][i], 0.3)
    return s.render(loop=False)


def song_defeat():
    s = Song(90, 2)
    s.lead([('E5', 4), ('D#5', 4), ('D5', 4), ('C#5', 12)], 0.14, 0.5)
    s.lead([('A3', 4), ('G#3', 4), ('G3', 4), ('F#3', 12)], 0.12, 0.5)
    return s.render(loop=False)


# ---- World 2 / summon / tower loops (kept short: each .ogg stays under ~80 KB)
def soft_pad(s, chords, steps_each, vol=0.05, octave=4, attack=0.25, detune=0.004):
    """Sine/triangle chord pad with a slow swell (gentler than Song.pad's squares)."""
    pos = 0
    while pos * s.step * SR < s.length:
        for (root, kind) in chords:
            dur = steps_each * s.step
            n = int(SR * dur)
            for f in chord_notes(root, kind, octave):
                sig = sine(f, dur) * 0.7 + tri(f * (1 + detune), dur) * 0.3
                s.add(sig * env(n, attack, 0.3, 0.75, min(0.4, dur * 0.3)), pos, vol)
            pos += steps_each


def bell_arp(s, chords, steps_each, vol=0.05, octave=6, rate=1, order=(0, 1, 2, 1), decay=7.0):
    pos = 0
    while pos * s.step * SR < s.length:
        for (root, kind) in chords:
            notes = chord_notes(root, kind, octave)
            for k in range(0, steps_each, rate):
                f = notes[order[(k // rate) % len(order)]]
                s.add(bell(f, 0.6, decay=decay), pos + k, vol)
            pos += steps_each


def timpani(s, at_steps, root='A', octave=2, vol=0.3):
    f = nf(root + str(octave))
    for st in at_steps:
        s.add(sine(f * 1.5, 0.35, f) * np.exp(-t_axis(0.35) * 9), st, vol)


@seeded(201)
def song_world2():
    s = Song(108, 8)
    ch = [('F', 'maj'), ('G', 'maj'), ('A', 'min'), ('F', 'maj'), ('D', 'min'), ('C', 'maj'), ('A#', 'maj'), ('C', 'maj')]
    soft_pad(s, ch, 16, vol=0.05, octave=4)
    s.bass([c[0] for c in ch], 16, octave=2, vol=0.26, pattern=[(0, 6), (7, 4), (12, 6)])
    bell_arp(s, ch, 16, vol=0.045, octave=5, rate=2, order=(0, 1, 2, 1, 2, 1, 0, 1), decay=6)
    lead = [('C5', 4), ('F5', 4), ('A5', 6), ('G5', 2), ('B5', 8), ('A5', 4), ('G5', 4),
            ('E5', 6), ('C5', 2), ('E5', 4), ('A5', 4), ('F5', 12), ('-', 4),
            ('D5', 4), ('F5', 4), ('A5', 8), ('G5', 4), ('E5', 4), ('C5', 8),
            ('D5', 4), ('F5', 4), ('A#5', 6), ('A5', 2), ('G5', 12), ('-', 4)]
    s.lead(lead, 0.1, 0.5)
    # sea breeze: slow filtered-noise swells, two per phrase
    n = s.length
    t = np.arange(n) / SR
    breeze = lowpass(noise(n / SR), 900) * (0.5 + 0.5 * np.sin(2 * np.pi * t / (n / SR / 4) - np.pi / 2)) * 0.12
    s.add(breeze, 0, 1.0)
    s.drums('x.........x.....', '........x.......', '....x.......x...', vol=0.18)
    return s.render()


@seeded(202)
def song_battle2():
    s = Song(162, 8)
    ch = [('D', 'min'), ('G', 'maj'), ('D', 'min'), ('C', 'maj'), ('D', 'min'), ('G', 'maj'), ('A#', 'maj'), ('C', 'maj')]
    s.bass([c[0] for c in ch], 16, octave=2, vol=0.32,
           pattern=[(0, 2), (12, 1), (0, 1), (0, 2), (10, 2), (0, 2), (12, 2), (7, 2), (5, 2)])
    s.arp(ch, 16, vol=0.045, octave=4, rate=1)
    a = [('D5', 2), ('E5', 2), ('F5', 4), ('A5', 4), ('B5', 2), ('A5', 2), ('G5', 4), ('B5', 4), ('D6', 4), ('B5', 4),
         ('A5', 6), ('F5', 2), ('D5', 12), ('-', 8), ('C5', 2), ('D5', 2)]
    b = [('F5', 4), ('E5', 2), ('D5', 2), ('A5', 4), ('F5', 4), ('G5', 4), ('B5', 4), ('D6', 8),
         ('C6', 4), ('A#5', 4), ('A5', 4), ('F5', 4), ('G5', 8), ('E5', 8)]
    pos = s.lead(a, 0.11, 0.25)
    s.lead(b, 0.11, 0.25, pos)
    s.lead([(n if n == '-' else n[:-1] + str(int(n[-1]) - 1), d) for n, d in a + b], 0.05, 0.5)   # octave-down double
    s.drums('x.x...x.x.x...x.', '....x.......x..x', 'x.x.x.x.x.x.x.xx', vol=0.3)
    return s.render()


@seeded(203)
def song_tower():
    s = Song(126, 8)
    ch = [('A', 'min'), ('A#', 'maj'), ('A', 'min'), ('C', 'maj'), ('D', 'min'), ('A#', 'maj'), ('C', 'sus'), ('E', 'maj')]
    s.pad(ch, 16, vol=0.05, octave=3)
    s.bass(['A'] * 8, 16, octave=2, vol=0.3, pattern=[(0, 2), (0, 2), (12, 2), (0, 2), (0, 2), (1, 2), (0, 2), (3, 2)])
    s.arp(ch, 16, vol=0.04, octave=5, rate=1)
    # a motif that climbs one step every bar
    motif = [(0, 2), (3, 2), (7, 4), (5, 2), (3, 2), (2, 4)]
    base = 69   # A4
    pos = 0
    for bar, lift in enumerate([0, 1, 3, 5, 5, 7, 8, 11]):
        for semi, st in motif:
            f = 440.0 * 2 ** ((base + lift + semi - 69) / 12)
            dur = st * s.step
            sig = square(f, dur * 0.9, 0.25) * env(int(SR * dur * 0.9), 0.004, 0.05, 0.7, min(0.06, dur * 0.3))
            s.add(sig, pos, 0.09)
            pos += st
    timpani(s, [i * 16 for i in range(8)] + [i * 16 + 10 for i in range(8)], 'A', 2, vol=0.3)
    s.drums('x.......x.......', '....x.......x...', '..x...x...x...x.', vol=0.2)
    return s.render()


@seeded(204)
def song_summon():
    s = Song(116, 8)
    ch = [('D', 'sus'), ('A#', 'maj'), ('C', 'maj'), ('D', 'maj'), ('D', 'sus'), ('G', 'min'), ('A#', 'maj'), ('A', 'sus')]
    soft_pad(s, ch, 16, vol=0.06, octave=4, attack=0.5, detune=0.006)
    bell_arp(s, ch, 16, vol=0.04, octave=6, rate=1, order=(0, 1, 2, 1, 2, 0, 1, 2), decay=9)
    bell_arp(s, ch, 16, vol=0.03, octave=5, rate=4, order=(0, 2, 1, 2), decay=4)
    s.bass([c[0] for c in ch], 16, octave=2, vol=0.18, pattern=[(0, 12), (7, 4)])
    n = s.length
    t = np.arange(n) / SR
    shimmer = highpass(noise(n / SR), 7000) * (0.5 + 0.5 * np.sin(2 * np.pi * t * 0.5)) * 0.025
    s.add(shimmer, 0, 1.0)
    return s.render()


MUSIC = {'menu': song_menu, 'world': song_world, 'battle': song_battle, 'boss': song_boss,
         'victory': song_victory, 'defeat': song_defeat,
         'world2': song_world2, 'battle2': song_battle2, 'tower': song_tower, 'summon': song_summon}


def main(sfx_only=False, only=None):
    """only: optional set of sfx/music names - regenerate just those files."""
    if only:
        unknown = set(only) - set(SFX) - set(MUSIC)
        if unknown:
            raise SystemExit('unknown sound name(s): ' + ', '.join(sorted(unknown)))
    for name, fn in SFX.items():
        if only and name not in only:
            continue
        write_wav(os.path.join(ROOT, 'assets/audio/sfx', name + '.wav'), fn())
    if sfx_only:
        print('sfx generated')
        return
    tmp = os.path.join(os.path.dirname(__file__), '_tmp.wav')
    for name, fn in MUSIC.items():
        if only and name not in only:
            continue
        write_wav(tmp, fn())
        out = os.path.join(ROOT, 'assets/audio/music', name + '.ogg')
        os.makedirs(os.path.dirname(out), exist_ok=True)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp, '-ar', '22050', '-ac', '1', '-c:a', 'libvorbis', '-q:a', '1', out], check=True)
    if os.path.exists(tmp):
        os.remove(tmp)
    print('audio generated' + (' (' + ', '.join(sorted(only)) + ')' if only else ''))


if __name__ == '__main__':
    import sys
    # python3 tools/make_audio.py                       everything
    # python3 tools/make_audio.py --sfx                 sound effects only
    # python3 tools/make_audio.py --only world2,claim   just the listed tracks / effects
    only = None
    if '--only' in sys.argv:
        i = sys.argv.index('--only')
        only = {n.strip() for n in sys.argv[i + 1].split(',') if n.strip()} if i + 1 < len(sys.argv) else set()
        if not only:
            raise SystemExit('--only needs a comma-separated list of names')
    main(sfx_only='--sfx' in sys.argv, only=only)
