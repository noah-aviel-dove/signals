#include "forge.h"

#include <assert.h>
#include <string.h>

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
                    assert(i == link->spec.arity);
                    goto end;
                case LINK_SRC_M:
                    assert(i == 1);
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
                    assert(0);
            }
            param_prototype = link->dispatch.args[i].type;
            assert(param && param < (1u << 9));
            dispatch->prototype |= param << (i * 8);
        }
        // Set dispatch->func here based on link->spec.name and dispatch_shapes
        end:
    }
    return 0;
}
