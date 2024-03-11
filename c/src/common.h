#pragma once

#include <stdbool.h>


#define _DIE(use_errno, ...) _die(use_errno, __FILE__, __func__, __LINE__, __VA_ARGS__)
#define _REJ(use_errno, cond, ...) (cond ? _DIE(use_errno, __VA_ARGS__) : (void)0)
#define _REQ(use_errno, cond, ...) REJ(!cond, use_errno, __VA_ARGS__)

#define DIE(...) _DIE(0, __VA_ARGS__)
#define REJ(...) _REJ(0, __VA_ARGS__)
#define REQ(...) _REQ(0, __VA_ARGS__)

#define DIE_EN(...) _DIE(1, __VA_ARGS__) 
#define REJ_EN(...) _DIE(1, __VA_ARGS__)
#define REQ_EN(...) _DIE(1, __VA_ARGS__)

#define _REJ_OP(a, b, OP, FMT) REJ(!(a OP b), "%" #FMT " " #OP " %" #FMT, a, b)
#define REQ_EQ_I(a, b) _REJ_OP(a, b, !=, d)
#define REQ_NE_I(a, b) _REJ_OP(a, b, ==, d)
#define REQ_LT_I(a, b) _REJ_OP(a, b, >=, d)
#define REQ_GT_I(a, b) _REJ_OP(a, b, <=, d)
#define REQ_LE_I(a, b) _REJ_OP(a, b, >, d)
#define REQ_GE_I(a, b) _REJ_OP(a, b, <, d)
//etc for float, long, unsigned



void _die(bool, const char*, const char*, int, const char*, ...);

