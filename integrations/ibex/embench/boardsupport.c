// SPDX-License-Identifier: GPL-3.0-or-later
#include "simple_system_common.h"
#include "support.h"

void initialise_board(void) {}

void __attribute__((noinline, externally_visible)) start_trigger(void) {
  pcount_enable(0);
  pcount_reset();
  pcount_enable(1);
}

void __attribute__((noinline, externally_visible)) stop_trigger(void) {
  pcount_enable(0);
}
