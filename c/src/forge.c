#include "forge.h"

#include <string.h>

#include "common.h"
#include "data.h"
#include "sig.h"
#include "links.h"


int forge(struct chain *chain) {
    struct sig_alloc_args state[chain->stack_end - 1];
    memset(state, 0, (chain->stack_end - 1) * sizeof state[0]);
    for (struct link_ll *head = chain->links; head; head = head->next) {
        struct link *link = &head->item;
        struct link_dispatch *dispatch = malloc(sizeof(struct link_dispatch));
        struct sig_alloc_args dispatch_shapes[LINK_MAX_ARITY];
        link->dispatch = dispatch;
        dispatch->prototype = 0u;
        for (int i = 0; i < LINKF_ARITY_MAX; ++i) {
            struct link_arg_source arg_source = link->args[i].source;
            linkf_prototype param_prototype;
            switch(arg_source.type) {
                case LINK_SRC_0:
                    REQ_EQ_I(i, link->spec.arity);
                    dispatch->func = (linkf_0)0;
                    goto end;
                case LINK_SRC_M:
                    REQ_EQ_I(i, 1);
                    dispatch->prototype = LINK_PROTO_M;
                    assert(link->sources[0].type == LINK_SRC_C);
                    state[link->sources[0].stack_index] = arg_source.alloc_args;
                    goto end;
                case LINK_SRC_C:
                    if (state[arg_source.stack_index].type == SIG_0) {
                        return 1;
                    } else {
                        dispatch->args[i] = &(chain->stack[arg_source.stack_index]);
                        dispatch_shapes[i] = state[arg_source.stack_index];
                    } 
                    break;
                case LINK_SRC_D:
                    // This fails with an assert given bad data ref
                    data_get(arg_source.data_key, dispatch->args[i]);
                    dispatch_shapes[i] = sig_args(dispatch->args[i]);
                    break;
                default:
                    DIE("%d", arg_source.type);
            }
            param_prototype = link->dispatch.args[i].type;
            REQ_GT_I(param_prototype, 0);
            REQ_LT_I(param_prototype, (1u << 9));
            dispatch->prototype |= param_prototype << (i * 8);
        }
        dispatch->func = linkf_get(link->spec, dispatch_shapes);
        end:
    }
    return 0;
}


union linkf linkf_get(const struct link_spec *spec, struct sig_alloc_args args[]) {
    struct linkfs fs = spec->fs;
    switch(spec->arity) {
        case 0:
            return fs._0;
        case 1:
            switch(args[0]) {
                case SIG_S:
                    return fs.s; 
                case SIG_V:
                    return fs.v;
                case SIG_B:
                    return fs.b;
            }
            DIE("");
        case 2:
            
        default:
            DIE("%d", spec->arity);
    }
}


//Does this still make sense?
union linkf linkf_get_(const char *name, enum link_prototype prototype) {
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
            DIE("%d", prototype);
            break;
    }
    return result;
}
