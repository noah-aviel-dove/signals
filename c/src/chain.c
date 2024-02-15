#include "chain.h"

#include <assert.h>

#include "sig.h"


void chain_init(struct chain *chain) {
    chain->stack = calloc(chain->stack_end, sizeof(struct sig));
}

void chain_exec(struct chain *chain, struct ctx *ctx) {
    for (struct link_ll *link_ll = chain->links; link_ll; link_ll = link_ll->next) {
        link_exec(ctx, &link_ll->item);
    }
    assert(chain->stack[0].type != SIG_0);
    for (int i = 1; i < chain->stack_end; ++i) {
        // Everything besides the result should be freed by links
        // Should it though? Why not re-use between executions?
        assert(chain->stack[i].type == SIG_0);
    }
}

