// SPDX-License-Identifier: Apache-2.0
#ifndef PIPESENSE_ARCH_TEST_MODEL_H
#define PIPESENSE_ARCH_TEST_MODEL_H

#define RVMODEL_BOOT

#define RVMODEL_DATA_BEGIN \
  .align 4; .global begin_signature; begin_signature:

#define RVMODEL_DATA_END \
  .align 4; .global end_signature; end_signature:

// Emit the raw signature bytes through Ibex Simple System's character device,
// then use its Spike-compatible tohost address to terminate simulation.
#define RVMODEL_HALT               \
  fence;                           \
  la x2, begin_signature;          \
  la x3, end_signature;            \
  li x4, 0x20000;                  \
1:                                \
  bgeu x2, x3, 2f;                 \
  lbu x1, 0(x2);                   \
  sw x1, 0(x4);                    \
  addi x2, x2, 1;                  \
  j 1b;                            \
2:                                \
  li x4, 0x20008;                  \
  li x1, 1;                        \
  sw x1, 0(x4);                    \
3:                                \
  j 3b;

#define RVMODEL_IO_INIT
#define RVMODEL_IO_WRITE_STR(_R, _STR)
#define RVMODEL_IO_CHECK()
#define RVMODEL_IO_ASSERT_GPR_EQ(_S, _R, _I)
#define RVMODEL_IO_ASSERT_SFPR_EQ(_F, _R, _I)
#define RVMODEL_IO_ASSERT_DFPR_EQ(_D, _R, _I)
#define RVMODEL_SET_MSW_INT
#define RVMODEL_CLEAR_MSW_INT
#define RVMODEL_CLEAR_MTIMER_INT
#define RVMODEL_CLEAR_MEXT_INT

#endif
