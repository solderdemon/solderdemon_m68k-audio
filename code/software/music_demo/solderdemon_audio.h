/* Generated copy of ../solderdemon_audio.h for the Docker build context. */
#ifndef SOLDERDEMON_M68K_AUDIO_H
#define SOLDERDEMON_M68K_AUDIO_H
#include <stdint.h>
#define SD_PSG_CLOCK_HZ 1843200UL
#define SD_PSG_ADDR 0x00f00101UL
#define SD_PSG_DATA 0x00f00103UL
/* Supervisor mode on MC68000/MC68010. Only this driver may own the PSG.
 * Hardware supplies all PSG timing; no software delay is needed.
 * Registers 14/15 (unexposed GPIO) are deliberately rejected.
 */
static inline int sd_psg_write(unsigned reg, uint8_t value) {
    uint16_t saved_sr;
    if (reg > 13) return -1;
    __asm__ volatile ("move.w %%sr,%0\n\tori.w #0x0700,%%sr"
                      : "=d" (saved_sr) : : "cc", "memory");
    *(volatile uint8_t *)SD_PSG_ADDR = (uint8_t)reg;
    *(volatile uint8_t *)SD_PSG_DATA = value;
    __asm__ volatile ("move.w %0,%%sr" : : "d" (saved_sr) : "cc", "memory");
    return 0;
}
static inline void sd_psg_silence(void) {
    sd_psg_write(8, 0); sd_psg_write(9, 0); sd_psg_write(10, 0);
}
#endif
