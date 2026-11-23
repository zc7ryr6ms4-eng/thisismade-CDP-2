"""Erzeugt eine 10-Sekunden-Stereo-WAV-Datei (440/660 Hz) für den Selbsttest."""
import math
import struct
import sys
import wave

rate, secs = 44100, 10
with wave.open(sys.argv[1] if len(sys.argv) > 1 else "tone.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(rate)
    frames = bytearray()
    for i in range(rate * secs):
        l = int(12000 * math.sin(2 * math.pi * 440 * i / rate))
        r = int(9000 * math.sin(2 * math.pi * 660 * i / rate))
        frames += struct.pack("<hh", l, r)
    w.writeframes(bytes(frames))
