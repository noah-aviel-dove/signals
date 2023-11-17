#include "links.h"

#include <assert.h>
#include <math.h>
#include <stdlib.h>


union linkf linkf_get(enum link_type link_type) {
    switch(link_type) {
#define PAIR(type, func, a) case type: return (union linkf){.a = &func}
        PAIR(LINK_BCLOCK, link_bclock, b );
        PAIR(LINK_ISINE,  link_isine,  b );
        PAIR(LINK_NOISE,  link_noise,  b );
        PAIR(LINK_ADD2 ,  link_add2 ,  bb_e);
        PAIR(LINK_MUL2 ,  link_mul_bb ,  bb_e);
#undef PAIR
        default:
            assert(0);
    }
}


void link_bclock(struct ctx *ctx, struct buf *b) {
    // Only fills 1st channel
    for (int i = 0; i < b->frames; ++i) {
        b->data[i] = i;
    }
}


void link_gclock(struct ctx *ctx, struct buf *b) {
    // Only fills 1st channel
    for (int i = 0; i < b->frames; ++i) {
        b->data[i] = ctx->frame + i;
    }
}


void link_isine(struct ctx *ctx, struct buf *b) {
    for (int i = 0; i < buf_size(b); ++i) {
        b->data[i] = sin(b->data[i]);
    }
}


void link_noise(struct ctx *ctx, struct buf *b) {
    srand((unsigned int)(ctx->seed + ctx->frame));
    for (int i = 0; i < buf_size(b); ++i) {
        b->data[i] = (sca)rand()/(sca)RAND_MAX;
    }
}


void link_add2(struct ctx *ctx, struct buf *b1, struct buf *b2) {
    assert(buf_size(b2) >= buf_size(b1));
    for (int i = 0; i < buf_size(b1); ++i) {
        b1->data[i] += b2->data[i];
    }
}


void link_mul_bb(struct ctx *ctx, struct buf *b1, struct buf *b2) {
    for (int i = 0; i < buf_size(b1); ++i) {
        b1->data[i] *= b2->data[i];
    }
}

void link_mul_bs(struct ctx *ctx, struct buf *b, sca *s) {
    for (int i = 0; i < buf_size(b); ++i) {
        b->data[i] *= *s;
    }
}
