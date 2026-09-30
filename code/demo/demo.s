/* GNU m68k assembler. Load demo.bin at 0x00040000, call in supervisor mode.
 * Plays a C major chord briefly, silences the PSG, and returns to firmware.
 */
    .equ PSG_ADDR, 0x00f00101
    .equ PSG_DATA, 0x00f00103
    .section .text
    .globl _start, psg_write, psg_silence
_start:
    movem.l %d0-%d2/%a0,-(%sp)
    bsr psg_silence
    lea chord(%pc),%a0
    moveq #0,%d0
1:  move.b (%a0)+,%d1
    bsr psg_write
    addq.b #1,%d0
    cmpi.b #14,%d0
    bne 1b
    move.l #1000000,%d2
2:  subq.l #1,%d2
    bne 2b
    bsr psg_silence
    movem.l (%sp)+,%d0-%d2/%a0
    rts
/* D0.b = register 0..13, D1.b = value. D0/D1 unchanged.
 * SR restored after each complete address/data pair; CCR outside call undefined.
 * Both MMIO writes must be indivisible relative to other PSG callers.
 */
psg_write:
    cmpi.b #13,%d0
    bhi 3f
    move.w %sr,-(%sp)
    ori.w #0x0700,%sr
    move.b %d0,PSG_ADDR
    move.b %d1,PSG_DATA
    move.w (%sp)+,%sr
3:  rts
psg_silence:
    movem.l %d0-%d1,-(%sp)
    moveq #0,%d1
    moveq #8,%d0
    bsr psg_write
    moveq #9,%d0
    bsr psg_write
    moveq #10,%d0
    bsr psg_write
    movem.l (%sp)+,%d0-%d1
    rts
chord:
    .byte 0xb8,1,0x5d,1,0x26,1,0,0x38,10,10,10,0,0,0
    .even
