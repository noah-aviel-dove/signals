#include "data.h"

#include <assert.h>
#include <stdlib.h>

#include "list.h"
#include "sig.h"


static struct map DATA;


void data_init(void) {
    map_init(&DATA, sizeof(struct sig), 32);
}


struct sig *data_get(key_t id) {
    return (struct sig*)map_get(&DATA, id);
}


void data_put(key_t id, struct sig *sig) {
    struct sig old;
    if (map_put(&DATA, id, sig, &old)) {
        sig_free(&old);
    }
}


sca *data_get_scalar(key_t id) {
    struct sig s;
    data_get(id, &s);
    assert(s.type == SIG_S);
    return s.val.s;
}


struct vec *data_get_vec(key_t id) {
    struct sig v;
    data_get(id, &v);
    assert(v.type == SIG_V);
    return v.val.v;
}


struct buf *data_get_buf(key_t id) {
    struct sig b; 
    data_get(id, &b);
    assert(b.type == SIG_B);
    return b.val.b;
}


void data_put_sca(key_t id, sca *s) {
    struct sig sig = {SIG_S, {.s = s}};
    data_put(id, &sig);
}


void data_put_vec(key_t id, struct vec *v) {
    struct sig sig = {SIG_V, {.v = v}};
    data_put(id, &sig);
}


void data_put_buf(key_t id, struct buf *b) {
    struct sig sig = {SIG_V, {.b = b}};
    data_put(id, &sig);
}


void data_rm(key_t id) {
    assert(map_pop(&DATA, id, 0));
}
