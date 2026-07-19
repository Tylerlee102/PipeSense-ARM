#ifndef PIPESENSE_EMBENCH_ASSERT_H
#define PIPESENSE_EMBENCH_ASSERT_H

#define assert(expression) do { if (!(expression)) while (1) {} } while (0)

#endif
