# SolderDemon m68k Audio — design intake

Status: requirements and interface investigation; NOT a fabrication-ready design.

## Confirmed requirement

Sound expansion card for SolderDemon m68k, built for the SolderDemon m68k expansion bus, using Yamaha YM2149 (proposed DIP-40 YM2149F).

## Local source inspection (2026-09-14)

- At project intake, the initial KiCad 10 schematic and PCB files were empty. The current project files are `solderdemon_m68k-audio.kicad_sch` and `solderdemon_m68k-audio.kicad_pcb`.
- ../rosco_6502-audio contains an existing YM2149F design, reference datasheets, audio mixer, footprints and generation tools. These are reusable references, not evidence of m68k bus compatibility.
- ../solderdemon_m68k-busboard/solderdemon_busboard.kicad_sch uses a 2x32 connector. Its signals include A1-A23, D0-D15, CPUCLK, E, VMA, VPA, AS, LDS, UDS, RW, RESET, DTACK, IOSEL and EXPSEL. Verify complete pin numbering and connector orientation against the actual target before layout.
- ../solderdemon_m68k/README.md describes a 10 MHz MC68010 configuration. The installed CPU, clock and hardware revision have not yet been confirmed.
- ../solderdemon_m68k/code/pld/address_decoder/ic2_address_decoder.pld maps IOSEL to the F00000-FFFFFF I/O region and excludes CPU-space cycles. IOSEL is not qualified with AS in that equation.
- The same decoder can automatically acknowledge expansion-space accesses when LGEXP selects that behavior. A slow peripheral must not assume it controls the duration of those cycles.
- ../solderdemon_m68k/code/pld/duartsel/ic3_duart_sel.pld decodes the onboard DUART at F00000-F0003F with LDS asserted. A new audio allocation must avoid this and other installed expansions.

## Proposed first-version requirements, pending user response

- Vertical expansion card compatible with the local m68k busboard.
- Through-hole parts and socketed YM2149F.
- Dedicated PSG clock; select frequency and tolerance using the Yamaha limits.
- Passive ABC stereo line output to a 3.5 mm jack, with an optional L/GND/R header.
- 5 V supply from the bus with local decoupling and bulk capacitance.
- Reset must put PSG control signals in the inactive state.

## Engineering work required

1. Confirm the target motherboard revision, CPU clock, connector mechanics and desired audio output.
2. Select a bus interface and address allocation. Compare direct hardware-timed PSG accesses with a latched software-controlled interface; do not carry over the 6502 VIA connection unchanged.
3. Verify byte-lane selection, address decoding, reset behavior, shared-line drive and bus-cycle termination.
4. Budget PSG setup, hold and strobe widths from the actual datasheet. Include interrupt and debugger effects if software controls pulse duration.
5. Create the schematic, review pin mappings and run ERC.
6. Place and route the PCB, check connector orientation, physical clearances, ground return and analog routing; run DRC and schematic parity checks.
7. Provide BOM, programming/demo software, manufacturing outputs and a first-power-on procedure. Hardware operation remains unverified until a physical prototype is tested.
