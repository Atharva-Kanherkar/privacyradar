#!/usr/bin/env python3
"""Original minimal dark score for the launch video. 23s, 44.1kHz stereo.

Structure mirrors the cut (30fps):
  0.0s   drone fades in, sparse pulse
  2.0s   word beats: hits at 2.0 / 2.9 / 3.8 / 4.7
  5.6s   riser into the receipt
  7.6s   impact; steady pulse under the typewriter
  11.9s  accent (stamp lands)
  13.4s  row ticks (chips at ~13.8 14.2 14.5 14.9 15.3)
  17.4s  thinner section (pitch)
  20.2s  final hit (outro), long tail fade
"""

import math
import random
import struct
import wave

SR = 44100
DUR = 23.0
N = int(SR * DUR)
random.seed(7)

left = [0.0] * N
right = [0.0] * N


def add(t0, samples, gain_l=1.0, gain_r=1.0):
    start = int(t0 * SR)
    for i, value in enumerate(samples):
        j = start + i
        if 0 <= j < N:
            left[j] += value * gain_l
            right[j] += value * gain_r


def kick(amp=0.5, length=0.35):
    n = int(length * SR)
    out = []
    for i in range(n):
        t = i / SR
        freq = 120 * math.exp(-t * 9) + 42
        env = math.exp(-t * 14)
        out.append(amp * env * math.sin(2 * math.pi * freq * t))
    return out


def boom(amp=0.55, length=1.2):
    n = int(length * SR)
    out = []
    for i in range(n):
        t = i / SR
        env = math.exp(-t * 3.2)
        out.append(amp * env * (math.sin(2 * math.pi * 48 * t) + 0.4 * math.sin(2 * math.pi * 96 * t)))
    return out


def hat(amp=0.10, length=0.05):
    n = int(length * SR)
    out = []
    prev = 0.0
    for i in range(n):
        t = i / SR
        white = random.uniform(-1, 1)
        hp = white - prev  # crude high-pass
        prev = white
        out.append(amp * math.exp(-t * 90) * hp)
    return out


def riser(amp=0.3, length=2.0):
    n = int(length * SR)
    out = []
    prev = 0.0
    for i in range(n):
        t = i / SR
        p = t / length
        white = random.uniform(-1, 1)
        smooth = prev + 0.12 * (white - prev)
        prev = smooth
        tone = math.sin(2 * math.pi * (90 + 240 * p * p) * t)
        out.append(amp * p * p * (0.6 * smooth + 0.4 * tone))
    return out


# Bass drone: two detuned sines, slow swell, ducks after the final hit.
for i in range(N):
    t = i / SR
    if t < 2.0:
        env = t / 2.0 * 0.16
    elif t < 20.2:
        env = 0.16
    else:
        env = 0.16 * max(0.0, 1 - (t - 20.2) / 2.4)
    wob = 1 + 0.12 * math.sin(2 * math.pi * 0.12 * t)
    value = env * wob * (math.sin(2 * math.pi * 55 * t) + 0.55 * math.sin(2 * math.pi * 55.35 * t + 0.7))
    left[i] += value
    right[i] += value * 0.94

# Sparse intro pulse
for t0 in (0.5, 1.25):
    add(t0, kick(0.28))

# Word beats
for t0 in (2.0, 2.9, 3.8, 4.7):
    add(t0, kick(0.5))
    add(t0 + 0.45, hat(0.09))

# Riser into the receipt
add(5.6, riser(0.32, 2.0))

# Impact + steady pulse under the typewriter (7.6 -> 13.4, every 0.75s)
add(7.6, boom(0.6))
pulse_t = 8.35
while pulse_t < 13.4:
    add(pulse_t, kick(0.34))
    add(pulse_t + 0.375, hat(0.07))
    pulse_t += 0.75

# Stamp accent
add(11.9, kick(0.5))

# Chip row ticks
for t0 in (13.8, 14.17, 14.53, 14.9, 15.27):
    add(t0, kick(0.3))
    add(t0 + 0.18, hat(0.08))

# Steady pulse through pitch section, thinner
pulse_t = 16.0
while pulse_t < 20.0:
    add(pulse_t, kick(0.26))
    pulse_t += 0.75

# Final hit + shimmer tail
add(20.2, boom(0.62, 1.6))
add(20.2, hat(0.12, 0.4))

# Master: soft clip, global fade-out over the last 1.2s
frames = bytearray()
for i in range(N):
    t = i / SR
    fade = min(1.0, (DUR - t) / 1.2)
    for channel in (left, right):
        value = math.tanh(channel[i] * 1.1) * 0.85 * fade
        frames += struct.pack("<h", max(-32767, min(32767, int(value * 32767))))

with wave.open("public/score.wav", "wb") as handle:
    handle.setnchannels(2)
    handle.setsampwidth(2)
    handle.setframerate(SR)
    handle.writeframes(bytes(frames))

print("wrote public/score.wav")
