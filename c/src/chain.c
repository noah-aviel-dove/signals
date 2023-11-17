#include "chain.h"

#include <assert.h>

#include "sig.h"


struct sig chain_exec(struct chain *chain, struct ctx *ctx) {
    struct sig result = {.type = SIG_0};
    assert(!chain->stack);
    chain->stack = calloc(chain->max_stack_size, sizeof(struct sig));
    for (int i = 0; i < chain->max_stack_size; ++i) {
        chain->stack[i].type = SIG_0;
    }
    for (struct link_ll *link_ll = chain->links; link_ll; link_ll = link_ll->next) {
        link_exec(ctx, chain, &link_ll->item);
    }
    for (int i = 0; i < chain->max_stack_size; ++i) {
        if (i == chain->result_index) {
            result = chain->stack[i];
        } else {
            // Everything besides the result should be freed by links
            assert(chain->stack[i].type == SIG_0);
        }
    }
    assert(result.type != SIG_0);
    free(chain->stack);
    chain->stack = NULL;
    return result;
}

