# Korobeiniki — m68k PSG trailer

30-second original chiptune arrangement of the traditional Korobeiniki melody,
familiar from Tetris, at 150 BPM for the SolderDemon m68k YM2149 card
(1.8432 MHz PSG clock). This is a new score, not a game audio recording.

0–3.2 s: melody solo on A (left). 3.2–6.4 s: centered bass enters on B.
6.4–12.8 s: plucked arpeggios enter on C (right). 12.8–25.6 s:
melody swaps to C, with vibrato and alternating arpeggios/noise drums on A.
25.6–30 s: A-minor final chord decays to silence. Plucks and drums use the
shared falling hardware envelope (shape 9); melody and bass have independent
software dynamics.

## Build and play

From this directory, with rosco CLI and Docker running:

```sh
python3 ../../../tools/generate_music_demo.py
rosco build --docker
rosco run --port /dev/ttyUSB0
```

The output is `music_demo.bin`, with ELF, map, and disassembly alongside it.
Use `rosco ports` to find your UART port. This uses rosco's serial startup and
linker script: load it through the firmware, unlike the raw subroutine in
`../demo`. Press any key to stop. Playback also ends automatically after 30 s.
All channels are muted before returning to the starter runtime, which reboots
back to firmware.

Supervisor mode and the firmware's 100 Hz timer interrupt must be enabled.
Playback follows `_TIMER_100HZ`, so CPU speed does not change the tempo. Late
frames are skipped. The player exclusively owns the PSG while running. The
existing `solderdemon_audio.h` driver makes atomic register/data byte writes at
$F00101/$F00103, restoring the interrupt mask after each pair. Registers 14/15
are never used. Connect powered speakers or an amplifier line input to J2/J3;
start with low amplifier volume (this is a passive line output).

## Edit and verify

Edit the score in `../../../tools/generate_music_demo.py` and regenerate. Edit
`player.c` for instrumentation and `kmain.c` for firmware playback.
Run `python3 ../../../tools/verify_music_demo.py` to check the actual C renderer
and generate an approximate stereo `music_demo-preview.wav`. The preview is
not a measurement of the board or its exact analog/DAC response.

Starter files/libraries were created with `rosco init --board rosco_m68k
--language c --docker --target hardware --yes`. Code is MIT as in the parent
card project; bundled rosco libraries retain their original licenses.
