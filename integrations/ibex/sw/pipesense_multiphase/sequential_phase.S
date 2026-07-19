// SPDX-License-Identifier: Apache-2.0
.section .text
.align 2
.global sequential_phase
.type sequential_phase, @function
sequential_phase:
  li t0, 192
1:
  .rept 64
    xor a0, a0, a1
    addi a0, a0, 7
  .endr
  addi t0, t0, -1
  bnez t0, 1b
  ret
.size sequential_phase, .-sequential_phase
