#include <stdio.h>
#include <machine.h>
#include "solderdemon_audio.h"
#include "player.h"

void kmain(void) {
    uint32_t start, tick, previous = UINT32_MAX;
    uint8_t regs[14];
    unsigned reg;
    printf("Korobeiniki / Tetris theme / SolderDemon m68k YM2149\r\n"
           "30 seconds, stereo. Press any key to stop.\r\n");
    sd_psg_silence();
    start = _TIMER_100HZ;
    while ((tick = (uint32_t)(_TIMER_100HZ - start)) < music_duration()) {
        int trigger;
        if (mcCheckchar()) { (void)mcReadchar(); break; }
        if (tick == previous) continue;
        trigger = music_frame(tick, regs);
        /* Also retrigger if a timer frame missed an eighth-note boundary. */
        if (previous == UINT32_MAX || tick / 20 != previous / 20) trigger = 1;
        for (reg = 0; reg < 13; ++reg) sd_psg_write(reg, regs[reg]);
        if (trigger) sd_psg_write(13, regs[13]);
        previous = tick;
    }
    sd_psg_silence();
    sd_psg_write(7, 0x3f);
    printf("Playback stopped.\r\n");
}
