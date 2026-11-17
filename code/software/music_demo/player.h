#ifndef MUSIC_PLAYER_H
#define MUSIC_PLAYER_H
#include <stdint.h>
/* Render a 100 Hz register image; true means retrigger R13. */
int music_frame(uint32_t tick, uint8_t regs[14]);
uint32_t music_duration(void);
#endif
