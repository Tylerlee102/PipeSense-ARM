// SPDX-License-Identifier: GPL-3.0-or-later
#include "simple_system_common.h"
#include "support.h"

#ifndef EMBENCH_NAME
#define EMBENCH_NAME unknown
#endif

#define STRINGIFY_INNER(value) #value
#define STRINGIFY(value) STRINGIFY_INNER(value)

int main(void) {
  volatile int result;

  initialise_board();
  initialise_benchmark();
  warm_caches(WARMUP_HEAT);
  start_trigger();
  result = benchmark();
  stop_trigger();

  if (!verify_benchmark(result)) {
    puts("EMBENCH_FAIL " STRINGIFY(EMBENCH_NAME) "\n");
    while (1) {}
  }

  puts("EMBENCH_PASS " STRINGIFY(EMBENCH_NAME) "\n");
  return 0;
}
