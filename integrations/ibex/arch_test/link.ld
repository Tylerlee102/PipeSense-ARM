OUTPUT_ARCH(riscv)
ENTRY(rvtest_entry_point)

MEMORY
{
  ram : ORIGIN = 0x00100000, LENGTH = 0x38000
}

tohost = 0x00020008;
fromhost = 0x00138010;

SECTIONS
{
  .text : {
    *(.text.init)
    *(.text)
    *(.text.*)
  } > ram

  .rodata : {
    *(.rodata)
    *(.rodata.*)
  } > ram

  .data : {
    *(.data)
    *(.data.*)
    *(.tohost)
  } > ram

  .bss (NOLOAD) : {
    *(.bss)
    *(.bss.*)
    *(COMMON)
  } > ram
}
