#include "link.h"

#include <assert.h>

#include "chain.h"
#include "data.h"


void link_exec(struct ctx *ctx, struct link *link) {
    struct link_spec *spec = link->spec;
    struct link_dispatch *dispatch = link->dispatch;
    switch(dispatch.prototype) {
        case LINK_PROTO_M:
            assert(link->sources[0].type == LINK_SRC_C);
            assert(link->sources[1].type == LINK_SRC_M);
            if (link->sources[1].alloc_args.type) {
                sig_alloc(dispatch.args[0], link->sources[1].alloc_args);
            } else {
                sig_free(dispatch.args[0]);
            }
            break;
        case LINK_PROTO_0:
            dispatch.func._0(ctx);
            break;
#define DISPATCH_1(A, a      ) case LINK_PROTO_##A                       : dispatch.func.a   (ctx, dispatch.args[0].a                    ); break
#define DISPATCH_2(A, B, a, b) case LINK_PROTO_##A | (LINK_PROTO##B << 8): dispatch.func.a##b(ctx, dispatch.args[0].a, dispatch.args[1].b); break
        DISPATCH_1(S, s);
        DISPATHC_1(V, v);
        DISPATHC_1(B, b);
        DISPATCH_2(S, S, s, s);
        DISPATCH_2(V, S, v, s);
        DISPATCH_2(V, V, v, v);
        DISPATCH_2(B, S, b, s);
        DISPATCH_2(B, V, b, v);
        DISPATCH_2(B, B, b, b);
#undef DISPATCH_1
#undef DISPATCH_2
        default:
            assert(0);
    }
}


struct link link_alloc(chain_stack_index index, struct sig_alloc_info info) {
    struct link link = {
        .fname = "ALOC",
        .prototype = LINK_PROTO_MA,
        .args = {
            {
                .spec = {.a = info},
                .type = LINK_SRC_MA
            },
            {
                .spec = {.c = index},
                .type = LINK_SRC_C
            }
        }
    };
    return link;
}


struct link link_free(chain_stack_index index) {
    struct link link = {
        .fname = "FREE",
        .prototype = LINK_PROTO_MF,
        .args = {{.spec = {.c = index}}}
    };
    return link;
}

