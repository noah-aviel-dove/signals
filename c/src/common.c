#include "common.h"

#include <stdio.h>
#include <stdarg.h>
#include <stdlib.h>


void _die(bool use_errno, const char *file, const char *func, int lineno, const char *fmt, ...) {
    va_list args;
    va_start(args, fmt);
    if (use_errno) {
        perror("Error");
    } else {
        fputs(stderr, "Error");
    }
    fprintf(stderr, "At %s:%s:%d\n", file, func, lineno);
    vfprintf(stderr, fmt, args);
    va_end(args);
    fputchar(stderr, '\n');
    exit(EXIT_FAILURE);
}

