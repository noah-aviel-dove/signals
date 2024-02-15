#include "links.h"

#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "map.h"


#define M_TAU (2 * M_PI)


static struct map LINKS;


void links_init(void) {
    map_init(&LINKS, sizeof(struct link_spec), 32);
    map_put(&LINKS, 
}


union linkf linkf_get(const char *name, enum link_prototype prototype) {
    struct link_spec spec;
    union linkf result;
    key_t key;
    strncpy(&key, name, LINK_NAME_MAX);
    map_get(&LINKS, key, &spec);
    switch (prototype) {
#define CASE(P, a) case LINK_PROTO_##P: assert(spec.a); result.a = spec.a; break;
    CASE(S, s)
    CASE(V, v)
    CASE(B, b)
    CASE(SS, ss)
    CASE(VS, vs)
    CASE(BS, bs)
    CASE(VV_EQ, vv_eq)
    CASE(VV_1L, vv_1l)
    CASE(VV_1G, vv_1g)
    CASE(BV_EQ, BV_EQ)
    CASE(BV_1L, bv_1l)
    CASE(BV_1G, bv_1g)
    CASE(BB_EQ, bb_eq)
    CASE(BB_1L, bb_1l)
    CASE(BB_1G, bb_1g)
#undef CASE
    case LINK_PROTO_0:
    case LINK_PROTO_MA:
    case LINK_PROTO_MF:
    default:
        assert(0);
        break;
    }
    return result;
}


void link_bclock(struct ctx *ctx, struct buf *b) {
    // Only fills 1st channel
    for (int i = 0; i < b->frames; ++i) {
        b->data[i] = i;
    }
}


void link_gclock(struct ctx *ctx, struct buf *b) {
    // Only fills 1st channel. What if I added a signal type "channel"? If so, rename "buffer" to "matrix"
    for (int i = ctx->frame; i < ctx->frame + b->frames; ++i) {
        b->data[i] = i;
    }
}


void link_isine(struct ctx *ctx, struct buf *b) {
    for (int i = 0; i < buf_size(b); ++i) {
        b->data[i] = sin(b->data[i]);
    }
}


void link_ipulse(struct ctx *ctx, struct buf *b, sca *s) {
    for (int i = 0; i < buf_size(b); ++i) {
        b->data[i] = copysign(1.0, M_PI - fmod(b->data[i], M_TAU));
    }
}


void link_itri1(struct ctx *ctx, struct buf *b, sca *s) {
    // This produces a very odd, discontinuous transition between triangle waves and sawtooth waves.
    // Keeping it so I can test it but need another version that implements a cleaner shuffle.
    const sca 
        a = *s, 
        a_abs = fabs(a),
        t1 = M_PI * (1 + a_abs),
        t2 = ((a + 3) * a + 2) / 4,
        t3 = 2 - abs_a,
        t4 = (abs_a + a - 2) / 2;

    for (int i = 0; i < buf_size(b); ++i) {
        b->data[i] = 2 * fabs(fmod(buf->data[i] / t1 - t2, t3) + t4) - 1;
    }
}


void link_itri2(struct ctx *ctx, struct buf *b, sca *s) {
    // This produces the expected transition behavior.
    const sca 
        a = *s,
        a1 = (1 - a) / 2;
     
    for (int i = 0; i < buf_size(b); ++i) {
        const sca 
            x = buf->data[i] / M_PI,
            d = fabs(fmod(x, 2) - 1),
            y = a + 2 * fmod(x - a1, 2);
        b->data[i] = d < a1 ? (y - 1) / (a - 1) : (y - 3) / (a + 1);
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
