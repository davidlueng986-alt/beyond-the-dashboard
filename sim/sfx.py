# Original sound design for Demo 2, synthesised from scratch (no samples, nothing to license).
import numpy as np, wave
SR, DUR = 48000, 11.0
N = int(SR * DUR); t = np.arange(N) / SR
rng = np.random.default_rng(7)
def band(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    m = 1 / (1 + (lo / np.maximum(f, 1e-6)) ** 6) if lo else 1.0
    m = m * (1 / (1 + (f / hi) ** 6)) if hi else m
    return np.fft.irfft(X * m, len(x))
def env(t0, a, d, n=N):
    e = np.zeros(n); i0 = int(t0 * SR); ia = max(1, int(a * SR)); idn = int(d * SR)
    seg = np.concatenate([np.linspace(0, 1, ia), np.exp(-np.linspace(0, 6, idn))])
    j = min(n, i0 + len(seg)); e[i0:j] = seg[:j - i0]; return e
def ss(a, b, x): u = np.clip((x - a) / (b - a), 0, 1); return u * u * (3 - 2 * u)
noise = rng.standard_normal(N)
L = np.zeros(N); R = np.zeros(N)
def add(x, pan=0.0, g=1.0):
    global L, R; L += x * g * (1 - max(0, pan)); R += x * g * (1 + min(0, pan))
ext = (t < 2.25) | (t >= 9.75)
# space drone (exterior) and cabin air (interior)
drone = (np.sin(2 * np.pi * 46 * t) * .5 + np.sin(2 * np.pi * 69.3 * t + .7) * .3 + np.sin(2 * np.pi * 92.4 * t) * .12) * (.75 + .25 * np.sin(2 * np.pi * .23 * t))
add(drone * (ss(0, .6, t) * (1 - ss(2.15, 2.3, t)) + ss(9.7, 9.9, t) * .8), 0, .16)
air = band(noise, 120, 1400) * .05 + band(noise, 0, 160) * .14
add(air * ss(2.2, 2.35, t) * (1 - ss(9.7, 9.8, t)), 0, .5)
# link telemetry blips, dying at 0.9-1.3, returning at 10.2
for k in np.arange(0.1, 1.3, 0.13):
    if k > .9 and rng.random() < .55: continue
    add(np.sin(2 * np.pi * (2400 + 300 * rng.random()) * t) * env(k, .002, .05), .4, .05)
for i, k in enumerate(np.arange(10.2, 10.9, 0.1)):
    add(np.sin(2 * np.pi * (1800 + 180 * i) * t) * env(k, .002, .07), .4, .06)
# link lost: sub drop
f = 62 * np.exp(-(t - .95) * 0.9); ph = 2 * np.pi * np.cumsum(f) / SR
add(np.sin(ph) * env(.95, .01, 1.6), 0, .5)
# cut to interior: impact
add(band(noise, 0, 220) * env(2.25, .002, .5) * 2.2 + np.sin(2 * np.pi * 48 * t) * env(2.25, .004, .9), 0, .55)
# alarm: soft two-note pulse breathing at 0.67 Hz, fading when the vent closes
al = (np.sin(2 * np.pi * 311 * t) + .5 * np.sin(2 * np.pi * 622 * t) + .25 * np.sin(2 * np.pi * 933 * t))
br = np.clip(np.sin(4.2 * t - 1.2), 0, 1) ** 2
add(band(al, 150, 1800) * br * ss(2.25, 2.5, t) * (1 - ss(8.5, 9.2, t)), -.2, .055)
# log ticks
for k in [2.5, 2.95, 3.45, 3.85, 4.25, 6.95, 7.35, 7.75, 8.05, 8.42, 9.1]:
    add(band(noise, 2500, 9000) * env(k, .001, .02) + np.sin(2 * np.pi * 3100 * t) * env(k + .02, .001, .03) * .5, -.5, .09)
# robot wake + flight
fw = 500 + 1100 * ss(3.72, 3.98, t); add(np.sin(2 * np.pi * np.cumsum(fw) / SR) * ss(3.72, 3.76, t) * (1 - ss(3.95, 4.05, t)), 0, .07)
u = ss(3.9, 6.9, t); speed = np.gradient(u * u * (3 - 2 * u) * .3 + u * .7, 1 / SR); speed = speed / speed.max()
pan = np.interp(t, [3.9, 6.9], [-.5, .4])
wh = band(noise, 300, 2600) * speed * .5 + np.sin(2 * np.pi * np.cumsum(140 + 120 * speed) / SR) * speed * .35
L += wh * .16 * (1 - np.maximum(0, pan)); R += wh * .16 * (1 + np.minimum(0, pan))
# scan
sc = ss(6.95, 7.0, t) * (1 - ss(7.5, 7.6, t)); add(np.sin(2 * np.pi * 2200 * t) * (np.sin(2 * np.pi * 22 * t) > 0) * sc, .3, .035)
# retraction: falling two-tone
add(np.sin(2 * np.pi * 740 * t) * env(7.35, .004, .16) + np.sin(2 * np.pi * 494 * t) * env(7.5, .004, .3), 0, .09)
# decision confirm
add(np.sin(2 * np.pi * 988 * t) * env(8.05, .003, .12), 0, .05)
# shutter: rumble then clunk
add(band(noise, 40, 420) * ss(8.42, 8.5, t) * (1 - ss(8.9, 8.97, t)), .35, .3)
add(band(noise, 0, 300) * env(8.95, .002, .25) * 2 + np.sin(2 * np.pi * 70 * t) * env(8.95, .003, .4), .35, .4)
# resolve: warm chord swell into the final exterior, bell when the link returns
pad = sum(np.sin(2 * np.pi * f0 * t + i) for i, f0 in enumerate([110, 164.8, 220, 277.2, 329.6])) / 5
add(pad * ss(8.9, 10.2, t), 0, .2)
bell = sum(np.sin(2 * np.pi * f0 * t) * a for f0, a in [(880, 1), (1320, .5), (1760, .25)])
add(bell * env(10.25, .004, 1.2), .2, .07)
fade = ss(0, .25, t) * (1 - ss(DUR - .35, DUR, t))
out = np.stack([L, R], 1) * fade[:, None]
out = np.tanh(out * 1.6) / 1.6; out = out / np.abs(out).max() * .82
w = wave.open('out/demo2_sfx.wav', 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((out * 32767).astype('<i2').tobytes()); w.close()
print('sfx ok', out.shape)
