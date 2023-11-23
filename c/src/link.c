#include "link.h"

#include <assert.h>

#include "chain.h"
#include "data.h"


enum link_source_type merge(enum link_source_type t1, enum link_source_type t2) {

    return 
}


void link_exec(struct ctx *ctx, struct chain *chain, struct link *link) {
    struct sig args[2];
    for (int i = 0; i < 2; ++i) {
        struct link_src src = link->src[i];
        switch (src.type) {
            case LINK_SRC_MA:
                assert(i == 0);
                assert(link->src[1].type == LINK_SRC_C);
                sig_alloc(&chain->stack[link->src[1].val.c], link->src[0].val.a);
                return;
            case LINK_SRC_MF:
                assert(i == 0);
                assert(link->src[1].type == LINK_SRC_C);
                sig_free(&chain->stack[link->src[1].c]);
                return;
            case LINK_SRC_C:
                args[i] = chain->stack[src.val.c];
                break;
            case LINK_SRC_D:
                args[i] = data_get(src.val.d);
                break;
            case LINK_SRC_0:
                assert(i == 1); 
                break;
            default:
                assert(0);
        }
    }
    assert(!((t1 | t2) & ~0xFF));
    assert(link->protype == link->prototype | t1 | t2 << 8);
    switch(link->prototype) {
#define DISPATCH_1(P, p, a1    ) case LINK_PROTO_##P: link->func.p(ctx, args[0].val.a1                ); break
#define DISPATCH_2(P, p, a1, a2) case LINK_PROTO_##P: link->func.p(ctx, args[0].val.a1, args[1].val.a2); break
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


struct link link_alloc(chain_stack_index index, struct sig_alloc_info *info) {
    return (struct link){
        .prototype = LINK_PROTO_MA,
        .src_type = LINK_SRC_C1 | LINK_SRC_A2,
        .src = {{.c = index}, {.a = info}},
        .func = {.m = '\0'}
    };
}


struct link link_free(chain_stack_index index) {
    return (struct link){
        .prototype = LINK_PROTO_MF,
        .src_type = LINK_SRC_C1,
        .src = {{.c = index}},
        .func = {.m = '\0'}
    };
}

