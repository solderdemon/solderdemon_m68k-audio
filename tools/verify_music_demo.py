#!/usr/bin/env python3
"""Exercise the real C score renderer and make an approximate ABC stereo preview.
Requires a host C compiler and numpy. Does not validate physical hardware.
"""
import ctypes
from pathlib import Path
import subprocess
import tempfile
import wave
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / 'code/software/music_demo'
CLOCK, RATE = 1843200, 44100

def main():
    with tempfile.TemporaryDirectory(prefix='music-demo-') as tmp:
        libpath = Path(tmp) / 'player.so'
        subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                        '-shared', '-fPIC', str(DEMO/'player.c'), '-o', str(libpath)], check=True)
        lib = ctypes.CDLL(str(libpath))
        lib.music_frame.argtypes = [ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint8)]
        r = (ctypes.c_uint8 * 14)()
        duration = lib.music_duration()
        assert duration == 3000
        frames = []
        for tick in range(duration + 1):
            trigger = lib.music_frame(tick, r)
            regs = list(r)
            assert regs[7] & 0xc0 == 0, 'PSG GPIO must stay inputs'
            assert all(regs[i] <= 15 for i in (1, 3, 5))
            assert all(regs[i] <= 16 for i in (8, 9, 10))
            if tick < duration:
                assert all(0 < (regs[i] | regs[i+1] << 8) <= 4095 for i in (0, 2, 4))
            frames.append((regs, trigger))
        assert frames[-1][0][8:11] == [0, 0, 0]
        assert frames[0][0][0:2] == [round(CLOCK/(16*659.255114)) & 255, 0]
        assert frames[1280][0][4] | frames[1280][0][5] << 8 == round(CLOCK/(16*659.255114))
        assert sum(t for _, t in frames) == 96
        assert any(r[7] & 0x38 != 0x38 for r, _ in frames[1280:2560])
        assert all(sum(v == 16 for v in r[8:11]) == 1 for r, _ in frames[640:2560])
        assert all(r[9] == 0 and r[10] == 0 for r, _ in frames[:320])
        assert all(r[10] == 0 for r, _ in frames[320:640])
        assert any(r[9] > 0 for r, _ in frames[320:640])
        assert frames[2999][0][8:11] == [0, 0, 0]
        # Evaluate frames in reverse to catch accidental state dependencies.
        for tick in range(duration, -1, -1):
            trigger = lib.music_frame(tick, r)
            assert (list(r), trigger) == frames[tick]

    # Approximate YM tone/noise gates and logarithmic DAC. Envelope period
    # is 128 master clocks per YM 32-step decrement (AY has 16 steps at 256).
    phase = np.zeros(3)
    noise_phase = 0.0
    noise_bit, lfsr = 1, 0x1ffff
    env_phase, env_level = 0.0, 0
    blocks = []
    volume = np.array([0.0] + [10**((v-31)*1.5/20) for v in range(1,32)])
    for regs, trigger in frames[:-1]:
        if trigger:
            env_phase, env_level = 0.0, 31
        size = RATE // 100
        periods = np.array([regs[i] | regs[i+1] << 8 for i in (0,2,4)])
        phase_steps = CLOCK / (16 * periods * RATE)
        positions = phase[:,None] + phase_steps[:,None] * np.arange(size)
        tones = positions % 1 < 0.5
        phase = (phase + phase_steps * size) % 1
        noise = np.empty(size, dtype=bool)
        envelope = np.empty(size)
        for j in range(size):
            noise_phase += CLOCK / (16 * max(1, regs[6]) * RATE)
            while noise_phase >= 1:
                noise_phase -= 1
                feedback = (lfsr ^ (lfsr >> 3)) & 1
                lfsr = (lfsr >> 1) | (feedback << 16)
                noise_bit = lfsr & 1
            noise[j] = noise_bit
            env_phase += CLOCK / (128 * max(1, regs[11] | regs[12]<<8) * RATE)
            while env_phase >= 1:
                env_phase -= 1
                env_level = max(0, env_level-1)
            envelope[j] = volume[env_level]
        voices = []
        for channel in range(3):
            gate = (tones[channel] | bool(regs[7] & (1 << channel))) & (noise | bool(regs[7] & (8 << channel)))
            level = regs[8+channel]
            amp = envelope if level == 16 else volume[level*2+1] if level else 0
            voices.append(gate * amp)
        a,b,c = voices
        blocks.append(np.column_stack((a + 0.455*b, c + 0.455*b)))
    audio = np.concatenate(blocks)
    # Approximate AC coupling by removing a slowly varying DC component.
    for channel in range(2):
        dc = 0.0
        for i in range(len(audio)):
            dc += 0.001 * (audio[i,channel] - dc)
            audio[i,channel] -= dc
    audio *= 0.85 / max(1.0, float(np.max(np.abs(audio))))
    path = DEMO/'music_demo-preview.wav'
    with wave.open(str(path), 'wb') as out:
        out.setparams((2,2,RATE,0,'NONE','not compressed'))
        out.writeframes((audio*32767).astype('<i2').tobytes())
    print('PASS: 3000 C-rendered frames; tuning, stereo voice swap, register ranges,')
    print('96 hardware-envelope triggers, noise, deterministic seeking, final mute.')
    print(f'Approximate 30-second stereo preview: {path}')

if __name__ == '__main__':
    main()
