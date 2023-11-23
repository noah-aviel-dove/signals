#include "chain.h"

#include <assert.h>

#include "sig.h"


struct sig chain_exec(struct chain *chain, struct ctx *ctx) {
    struct sig result;
    assert(!chain->stack);
    chain->stack = calloc(chain->stack_end, sizeof(struct sig));
    for (int i = 0; i < chain->stack_end; ++i) {
        chain->stack[i].type = SIG_0;
    }
    for (struct link_ll *link_ll = chain->links; link_ll; link_ll = link_ll->next) {
        link_exec(ctx, chain, &link_ll->item);
    }
    result = chain->stack[0];
    assert(result.type != SIG_0);
    for (int i = 1; i < chain->stack_end; ++i) {
        // Everything besides the result should be freed by links
        assert(chain->stack[i].type == SIG_0);
    }
    free(chain->stack);
    chain->stack = NULL;
    return result;
}

