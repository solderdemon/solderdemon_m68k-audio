ENTRY(_start)
SECTIONS {
  . = 0x00040000;
  .text : { *(.text*) *(.rodata*) }
  .data : { *(.data*) }
  .bss (NOLOAD) : { *(.bss*) *(COMMON) }
}
