#include "sig.h"

#include <assert.h>
#include <stdlib.h>


struct sig_alloc_args sig_args(struct sig *sig) {
    struct sig_alloc_args result;
    result.type = sig->type;
    switch(sig->type) {
        case SIG_0:
        case SIG_S:
            result.size = {0, 0};
            break;
        case SIG_V:
            result.size = {sig->v.size, 0};
            break;
        case SIG_B:
            result.size = {sig->b.channles, sig->b.frames};
            break;
        default:
            assert(0);
    }
    return result;
}


void sig_alloc(struct sig *sig, struct sig_alloc_args args) {
    assert(sig->type == SIG_0);
    sig->type = args.type;
    switch (sig->type) {
        case SIG_S:
            assert(!args.size[0])
            assert(!args.size[1])
            sig->val.s = sca_alloc();
            break;
        case SIG_V:
            assert(!args.size[1])
            sig->val.v = vec_alloc(args->size[0]);
            break;
        case SIG_B:
            sig->val.b = buf_alloc(args->size[0], info->size[1]);
            break;
        default:
            assert(0);
    }
}


sca *sca_alloc(void) {
    return malloc(sizeof(sca));
}


struct vec *vec_alloc(int size) {
    struct vec *vec = malloc(sizeof(vec) + size * (sizeof vec->data[0]));
    vec->size = size;
    return vec;
}


struct buf *buf_alloc(int channels, int frames) {
    struct buf *buf = malloc(sizeof(buf) + channels * frames * (sizeof buf->data[0]));
    buf->channels = channels;
    buf->frames = frames;
    return buf;
}


void sig_free(struct sig *sig) {
    switch(sig->type) {
#define CASE(T, a) case SIG_##T: free(sig->val.a); sig->val.a = NULL; sig->type = SIG_0; break
        CASE(S, s);
        CASE(V, v);
        CASE(B, b);
#undef CASE
        default:
            assert(0);
    }
}


#define CHECK_TYPES(src_type, dst_type) \
    assert(src->type == src_type);      \
    assert(dst->type == SIG_0);         \
    dst->type = dst_type;


void vtos(struct sig *dst, struct sig *src) {
    CHECK_TYPES(SIG_V, SIG_S)
    dst->s = sca_alloc();
    *(dst->s) = src->v.size ? src->v.data[0] : 0;
}


void btos(struct sig *dst, struct sig *src) {
    CHECK_TYPES(SIG_B, SIG_S)
    dst->s = sca_alloc();
    *(dst->s) = buf_size(src->b) ? src->b.data[0] : 0;
}


void stov(struct sig *dst, struct sig *src) {
    CHECK_TYPES(SIG_S, SIG_V)
    dst->v = vec_alloc(1);
    dst->v.data[0] = *(src->s);
}


void btov(struct sig *dst, struct sig *src) {
    CHECK_TYPES(SIG_B, SIG_V)
    dst->v = vec_alloc(src->b.channels);
    for (int i = 0; i < dst->v.size; ++i) {
        dst->v.data[i] = src->b.data[i * src->b,frames];
    }
}


void stob(struct sig *dst, struct sig *src) {
    CHECK_TYPES(SIG_S, SIG_B)
    dst->b = buf_alloc(1, 1);
    dst->b.data[0] = *(src->s);
}


void vtob(struct sig *dst, struct sig *src) {
    CHECK_TYPES(SIG_V, SIG_B)
    dst->b = buf_alloc(src->v.size, 1);
    memcpy(dst->b.data, src->v.data, src->v.size * sizeof src->v.data[0]);
}

#undef CHECK_TYPES


int buf_size(struct buf *buf) {
    return buf->channels * buf->frames;
}

