#ifndef PIPESENSE_EMBENCH_STDLIB_H
#define PIPESENSE_EMBENCH_STDLIB_H

#include <stddef.h>

#ifndef NULL
#define NULL ((void *)0)
#endif

#ifndef RAND_MAX
#define RAND_MAX 32767
#endif

void abort(void) __attribute__((noreturn));

#endif
