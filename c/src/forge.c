#include "forge.h"

#include <assert.h>

#include "data.h"
#include "links.h"


int forge(struct chain *c) {
    struct alloc_info state[chain->stack_end - 1] = {0};

    for (struct link_ll *head = chain->links; head; head = head->next) {
        struct link *link = &head->item;
        if (link->prototype == LINK_PROTO_MA) {
            chain_stack_index new = link->src[0].val.c;
            if (state[new].type == SIG_0) {
                state[new] = link->src[1].val.a;
            } else {
                return 1;
            }
        } else if (head->item.prototype == LINK_PROTO_MF) {
            chain_stack_index old = link->src[0].val.c;
            if (state[old].type != SIG_0) {
                state[old] = {0};
            } else {
                return 1;
            }
        } else {
            enum sig_type type;
            for (int i = 0; i < 2; ++i) {
                switch(link->src[i].type) {
                    case LINK_SRC_0:
                        type = SIG_0;
                        break;
                    case LINK_SRC_D:
                        type = data_get(link->src[i].val.d).type;
                        break;
                    case LINK_SRC_C:
                        type = state[link->src[i].val.c].type;
                        break;
                    default:
                        assert(0);
                }
            }
            assert(!(arg_types[0] | arg_types[1]))
            link->func = linkf_get(link->name);
        }
    }
}
