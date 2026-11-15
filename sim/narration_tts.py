import sys, json, soundfile as sf, numpy as np
from kokoro_onnx import Kokoro
k = Kokoro('kokoro-v1.0.onnx', 'voices-v1.0.bin')
lines = json.load(open(sys.argv[1]))
voice = sys.argv[2] if len(sys.argv) > 2 else 'am_michael'
for i, (txt, speed) in enumerate(lines):
    a, sr = k.create(txt, voice=voice, speed=speed, lang='en-us')
    sf.write(f'line{i+1}_{voice}.wav', a, sr); print(i + 1, voice, round(len(a) / sr, 2), 's')
