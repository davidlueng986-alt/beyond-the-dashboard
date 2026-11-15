# quiet original music bed: slow pad, low pulse, rises into the final card
import numpy as np, wave
SR, D = 48000, 30.0; t = np.arange(int(SR * D)) / SR
def ss(a, b, x): u = np.clip((x - a) / (b - a), 0, 1); return u * u * (3 - 2 * u)
def chord(fs, t0, t1):
    e = ss(t0, t0 + 1.2, t) * (1 - ss(t1 - .8, t1 + .4, t)); return e * sum(np.sin(2 * np.pi * f * t + i) / (1 + i * .4) for i, f in enumerate(fs))
pad = chord([65.4, 98, 130.8, 155.6], 0, 11.2) + chord([58.3, 87.3, 116.5, 146.8], 11.0, 17.9) + chord([55, 82.4, 110, 130.8, 164.8], 17.8, 28.6) + chord([65.4, 98, 130.8, 164.8, 196], 28.3, 30.5) * 1.4
shimmer = sum(np.sin(2 * np.pi * f * t) for f in [523.3, 659.3, 784]) * (.5 + .5 * np.sin(2 * np.pi * .25 * t)) * .08 * (ss(0, 3, t) * (1 - ss(10, 11.5, t)) + ss(28.3, 29, t))
pulse = np.sin(2 * np.pi * 49 * t) * (np.maximum(0, np.sin(2 * np.pi * 1.1 * t)) ** 8) * ss(4.7, 6, t) * (1 - ss(10.5, 11, t)) * .8
out = (pad * .55 + shimmer + pulse) * ss(0, 1.5, t) * (1 - ss(29.3, 30, t))
L = out + np.roll(out, 900) * .3; R = out * .9 + np.roll(out, 1500) * .35
st = np.stack([L, R], 1); st = st / np.abs(st).max() * .5
w = wave.open('mix/bed.wav', 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype('<i2').tobytes()); w.close(); print('bed ok')
