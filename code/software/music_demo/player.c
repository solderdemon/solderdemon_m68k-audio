#include "player.h"
#include "score.h"

static void tone(uint8_t *r, unsigned voice, unsigned note, int bend) {
    unsigned p = periods[note - 36] + bend;
    r[voice * 2] = (uint8_t)p;
    r[voice * 2 + 1] = (uint8_t)(p >> 8);
}
uint32_t music_duration(void) { return MUSIC_TOTAL_TICKS; }
int music_frame(uint32_t tick, uint8_t r[14]) {
    static const int8_t vibrato[16] = {0,0,1,1,1,1,1,0,0,0,-1,-1,-1,-1,-1,0};
    static const uint8_t triads[3][4] = {{57,60,64,69}, {52,56,59,64}, {50,53,57,62}};
    unsigned i, pos, age, duration, bar, step, phase, chord, lead, accompaniment;
    for (i = 0; i < 14; ++i) r[i] = 0;
    r[7] = 0x3f; /* GPIO direction bits stay zero (inputs). */
    if (tick >= MUSIC_TOTAL_TICKS) return 0;
    r[7] = 0x38;
    r[11] = 64; /* YM envelope step = 128 * period / PSG clock. */
    r[13] = 9;  /* Falling one-shot, hold at zero. */
    if (tick >= 2560) {
        unsigned fade = (tick - 2560) / 29;
        tone(r, 0, 72, 0); tone(r, 1, 45, 0); tone(r, 2, 76, 0);
        r[8] = r[9] = r[10] = (uint8_t)(fade < 15 ? 15 - fade : 0);
        return 0;
    }
    pos = tick % MUSIC_THEME_TICKS;
    age = pos;
    for (i = 0; i < sizeof melody / sizeof melody[0]; ++i) {
        if (age < melody[i].ticks) break;
        age -= melody[i].ticks;
    }
    duration = melody[i].ticks;
    bar = pos / 160; step = (pos / 20) % 8; phase = pos % 20;
    chord = chords[bar];
    lead = tick < 1280 ? 0 : 2; accompaniment = 2 - lead;
    tone(r, lead, melody[i].midi,
         tick >= 1280 && age > 10 ? vibrato[(age / 2) % 16] : 0);
    r[8 + lead] = age >= duration - 4 ? 0 : (age < 3 ? 14 : 12);
    tone(r, 1, chord == 0 ? 45 : (chord == 1 ? 40 : 50), 0);
    r[9] = (uint8_t)(phase < 3 ? 13 : (phase < 16 ? 10 : 0));
    tone(r, accompaniment, triads[chord][step % 4], 0);
    r[8 + accompaniment] = 16;
    if (tick >= 1280 && (step & 1)) {
        /* Tone disabled on the noise voice, so it cannot gate the drum. */
        r[7] = (uint8_t)((0x38 | (1u << accompaniment)) & ~(8u << accompaniment));
        r[6] = (step == 3 || step == 7) ? 18 : 3;
        r[11] = (step == 3 || step == 7) ? 32 : 8;
    }
    /* Layer the introduction without changing the melody's musical time. */
    if (tick < 320) r[9] = 0;
    if (tick < 640) r[8 + accompaniment] = 0;
    return tick >= 640 && phase == 0;
}
