#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include "m68k.h"
static unsigned char mem[0x100000],regs[16];
static unsigned selected=255,pairs=0,writes=0,seen_chord=0;
int interrupt_ack_handler(unsigned int n){return M68K_INT_ACK_AUTOVECTOR;}
unsigned int m68k_read_memory_8(unsigned int a){assert(a<sizeof mem);return mem[a];}
unsigned int m68k_read_memory_16(unsigned int a){return (m68k_read_memory_8(a)<<8)|m68k_read_memory_8(a+1);}
unsigned int m68k_read_memory_32(unsigned int a){return (m68k_read_memory_16(a)<<16)|m68k_read_memory_16(a+2);}
void m68k_write_memory_8(unsigned int a,unsigned int v){
 if(a>=0xf00000){
  assert(a==0xf00101||a==0xf00103);assert((m68k_get_reg(NULL,M68K_REG_SR)&0x700)==0x700);writes++;
  if(a==0xf00101){assert(selected==255);assert(v<=13);selected=v;}
  else {assert(selected!=255);unsigned expected=pairs<3?8+pairs:(pairs<17?pairs-3:8+pairs-17);assert(selected==expected);regs[selected]=v;selected=255;pairs++;
   if(pairs==17){assert(regs[0]==0xb8&&regs[1]==1&&regs[2]==0x5d&&regs[3]==1&&regs[4]==0x26&&regs[5]==1&&regs[7]==0x38);assert(regs[8]==10&&regs[9]==10&&regs[10]==10);seen_chord=1;}
  }return;
 }
 assert(a<sizeof mem);mem[a]=v;
}
void m68k_write_memory_16(unsigned int a,unsigned int v){assert(a<0xf00000);m68k_write_memory_8(a,v>>8);m68k_write_memory_8(a+1,v);}
void m68k_write_memory_32(unsigned int a,unsigned int v){assert(a<0xf00000);m68k_write_memory_16(a,v>>16);m68k_write_memory_16(a+2,v);}
int main(int argc,char **argv){
 assert(argc==2);FILE*f=fopen(argv[1],"rb");assert(f);assert(fread(mem+0x40000,1,4096,f)==126);fclose(f);
 m68k_write_memory_32(0,0x80000);m68k_write_memory_32(4,0x40000);m68k_write_memory_32(0x80000,0x30000);
 m68k_init();m68k_set_cpu_type(M68K_CPU_TYPE_68010);m68k_pulse_reset();m68k_set_reg(M68K_REG_SR,0x2300);
 m68k_set_reg(M68K_REG_D0,0x12345678);m68k_set_reg(M68K_REG_D1,0x89abcdef);m68k_set_reg(M68K_REG_D2,0x34567890);m68k_set_reg(M68K_REG_A0,0x10000);
 unsigned steps=0;while(m68k_get_reg(NULL,M68K_REG_PC)!=0x30000&&steps++<3000000)m68k_execute(1);
 assert(steps<3000000);assert(pairs==20&&writes==40&&seen_chord&&selected==255);assert(regs[8]==0&&regs[9]==0&&regs[10]==0);
 assert(m68k_get_reg(NULL,M68K_REG_D0)==0x12345678);assert(m68k_get_reg(NULL,M68K_REG_D1)==0x89abcdef);assert(m68k_get_reg(NULL,M68K_REG_D2)==0x34567890);assert(m68k_get_reg(NULL,M68K_REG_A0)==0x10000);assert(m68k_get_reg(NULL,M68K_REG_SP)==0x80004);assert((m68k_get_reg(NULL,M68K_REG_SR)&0xff00)==0x2300);
 puts("PASS: compiled 126-byte demo executed on Musashi MC68010; 40 byte MMIO writes, 20 atomic register pairs, correct C-major periods, final mute, caller registers/stack/interrupt mask restored. No physical PSG emulation or analog validation.");return 0;
}
int illegal_instruction_handler(int opcode){fprintf(stderr,"Unexpected illegal opcode: %x\n",opcode);assert(0);return 0;}
