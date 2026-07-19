// SPDX-License-Identifier: Apache-2.0
#include "simple_system_common.h"

__attribute__((noinline)) static uint32_t add_path(uint32_t value, uint32_t step) {
  return value + (step ^ 0x9e3779b9u);
}

__attribute__((noinline)) static uint32_t xor_path(uint32_t value, uint32_t step) {
  return (value ^ (step + 0x7f4a7c15u)) + 3u;
}

static uint32_t branch_phase(uint32_t value, uint32_t phase) {
  for (uint32_t i = 0; i < 2048; ++i) {
    value = value * 1664525u + 1013904223u + phase;
    if (value & 0x20u) {
      value = add_path(value, i);
    } else {
      value = xor_path(value, i);
    }
  }
  return value;
}

extern uint32_t sequential_phase(uint32_t value, uint32_t phase);

int main(void) {
  uint32_t checksum = 0x12345678u;

  pcount_enable(0);
  pcount_reset();
  pcount_enable(1);

  for (uint32_t phase = 0; phase < 8; ++phase) {
    checksum = branch_phase(checksum, phase);
    checksum = sequential_phase(checksum, phase);
  }

  pcount_enable(0);
  if (checksum != 0xde332f10u) {
    puts("PIPESENSE_MULTIPHASE_FAIL ");
    puthex(checksum);
    putchar('\n');
    while (1) {}
  }
  puts("PIPESENSE_MULTIPHASE_PASS ");
  puthex(checksum);
  putchar('\n');
  return 0;
}
