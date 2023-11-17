#include "sig.h"

#include <assert.h>
#include <stdlib.h>


void sig_alloc(struct sig *sig, struct sig_alloc_info *info) {
    assert(sig->type == SIG_0);
    sig->type = info->type;
    switch (sig->type) {
        case SIG_S:
            sig->val.s = malloc(sizeof(sca));
            break;
        case SIG_V:
            sig->val.v = vec_alloc(info->size[0]);
            break;
        case SIG_B:
            sig->val.b = buf_alloc(info->size[0], info->size[1]);
            break;
        default:
            assert(0);
    }
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


int buf_size(struct buf *buf) {
    return buf->channels * buf->frames;
}

