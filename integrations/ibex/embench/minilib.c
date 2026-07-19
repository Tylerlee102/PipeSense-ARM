// SPDX-License-Identifier: GPL-3.0-or-later
#include <stdarg.h>
#include <stddef.h>
#include "simple_system_common.h"

void *memcpy(void *dest, const void *src, size_t count) {
  unsigned char *out = dest;
  const unsigned char *in = src;
  while (count--) *out++ = *in++;
  return dest;
}

void *memmove(void *dest, const void *src, size_t count) {
  unsigned char *out = dest;
  const unsigned char *in = src;
  if (out <= in) return memcpy(dest, src, count);
  while (count--) out[count] = in[count];
  return dest;
}

void *memset(void *dest, int value, size_t count) {
  unsigned char *out = dest;
  while (count--) *out++ = (unsigned char)value;
  return dest;
}

int memcmp(const void *left, const void *right, size_t count) {
  const unsigned char *a = left;
  const unsigned char *b = right;
  while (count--) {
    if (*a != *b) return (int)*a - (int)*b;
    ++a;
    ++b;
  }
  return 0;
}

size_t strlen(const char *text) {
  const char *end = text;
  while (*end) ++end;
  return (size_t)(end - text);
}

char *strchr(const char *text, int character) {
  do {
    if (*text == (char)character) return (char *)text;
  } while (*text++);
  return NULL;
}

int isdigit(int character) { return character >= '0' && character <= '9'; }

int isspace(int character) {
  return character == ' ' || character == '\t' || character == '\n' ||
         character == '\r' || character == '\f' || character == '\v';
}

int isxdigit(int character) {
  return isdigit(character) || (character >= 'a' && character <= 'f') ||
         (character >= 'A' && character <= 'F');
}

int tolower(int character) {
  return character >= 'A' && character <= 'Z' ? character + ('a' - 'A') : character;
}

void abort(void) { while (1) {} }

double fabs(double value) { return value < 0.0 ? -value : value; }
float fabsf(float value) { return value < 0.0f ? -value : value; }

double sqrt(double value) {
  if (value <= 0.0) return 0.0;
  double estimate = value > 1.0 ? value : 1.0;
  for (int i = 0; i < 24; ++i) estimate = 0.5 * (estimate + value / estimate);
  return estimate;
}

static void print_unsigned(unsigned int value, unsigned int base) {
  char digits[16];
  int count = 0;
  do {
    unsigned int digit = value % base;
    digits[count++] = (char)(digit < 10 ? '0' + digit : 'a' + digit - 10);
    value /= base;
  } while (value);
  while (count) putchar(digits[--count]);
}

int printf(const char *format, ...) {
  va_list args;
  va_start(args, format);
  while (*format) {
    if (*format++ != '%') {
      putchar(format[-1]);
      continue;
    }
    while (*format >= '0' && *format <= '9') ++format;
    if (*format == '.') {
      ++format;
      while (*format >= '0' && *format <= '9') ++format;
    }
    if (*format == 'l') ++format;
    switch (*format++) {
      case 's': puts(va_arg(args, const char *)); break;
      case 'c': putchar(va_arg(args, int)); break;
      case 'd':
      case 'i': {
        int value = va_arg(args, int);
        if (value < 0) { putchar('-'); value = -value; }
        print_unsigned((unsigned int)value, 10);
        break;
      }
      case 'u': print_unsigned(va_arg(args, unsigned int), 10); break;
      case 'x': print_unsigned(va_arg(args, unsigned int), 16); break;
      case '%': putchar('%'); break;
      default: break;
    }
  }
  va_end(args);
  return 0;
}
