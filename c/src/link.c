#include "link.h"

#include <assert.h>

#include "chain.h"
#include "data.h"


void link_exec(struct ctx *ctx, struct chain *chain, struct link *link) {
    if (link->prototype == LINK_PROTO_MA) {
        assert(link->src_type == (LINK_SRC_C1 | LINK_SRC_A2));
        sig_alloc(&chain->stack[link->src[0].c], link->src[1].a);
    } else if (link->prototype == LINK_PROTO_MF) {
        assert(link->src_type == LINK_SRC_C1);
        sig_free(&chain->stack[link->src[0].c]);
    } else {
        struct sig arg1, arg2;

        if (link->src_type & LINK_SRC_C1) {
            arg1 = chain->stack[link->src[0].c];
        } else if (link->src_type & LINK_SRC_D1) {
            arg1 = data_get(link->src[0].d);
        } else {
            assert(0);
        }

        if (link->src_type & LINK_SRC_C2) {
            arg2 = chain->stack[link->src[1].c];
        } else if (link->src_type & LINK_SRC_D2) {
            arg2 = data_get(link->src[1].d);
        } else {
            // Unary function, leave arg2 unassigned
        }

        switch(link->prototype) {
#define DISPATCH_1(P, p, a1    ) case LINK_PROTO_##P: link->func.p(ctx, arg1.val.a1             ); break
#define DISPATCH_2(P, p, a1, a2) case LINK_PROTO_##P: link->func.p(ctx, arg1.val.a1, arg2.val.a2); break
            DISPATCH_1(S,     s,     s   );
            DISPATCH_1(V,     v,     v   );
            DISPATCH_1(B,     b,     b   );
            DISPATCH_2(SS,    ss,    s, s);
            DISPATCH_2(VS,    vs,    v, s);
            DISPATCH_2(VV_E,  vv_e,  v, v);
            DISPATCH_2(VV_1F, vv_1f, v, v);
            DISPATCH_2(VV_1M, vv_1m, v, v);
            DISPATCH_2(BS,    bs,    b, s);
            DISPATCH_2(BV_E,  bv_e,  b, v);
            DISPATCH_2(BV_1F, bv_1f, b, v);
            DISPATCH_2(BV_1M, bv_1m, b, v);
            DISPATCH_2(BB_E,  bb_e,  b, b);
            DISPATCH_2(BB_1F, bb_1f, b, b);
            DISPATCH_2(BB_1M, bb_1m, b, b);
#undef DISPATCH_1
#undef DISPATCH_2
            default:
                assert(0);
        }
    }
}


struct link link_alloc(stack_index index, struct sig_alloc_info *info) {
    return (struct link){
        .prototype = LINK_PROTO_MA,
        .src_type = LINK_SRC_C1 | LINK_SRC_A2,
        .src = {{.c = index}, {.a = info}},
        .func = {.m = '\0'}
    };
}


struct link link_free(stack_index index) {
    return (struct link){
        .prototype = LINK_PROTO_MF,
        .src_type = LINK_SRC_C1,
        .src = {{.c = index}},
        .func = {.m = '\0'}
    };
}

