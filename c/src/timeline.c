#include <stdlib.h>

#include "timeline.h"


void tl_init(struct timeline *tl, int frames) {
    tl->frames = frames;
    tl->chains = calloc(frames, sizeof(struct chain_pll*));
}


void tl_free(struct timeline *tl) {
    for (struct chain_pll **c = tl->chains, **d = c + tl->frames; c < d; ++c) {
        while (*c) {
            struct chain_pll *cn = (*c)->next;
            free(*c);
            *c = cn;
        }
    }
    free(tl->chains);
}


void tl_add(struct timeline *tl, int frame, struct chain *chain) {
    struct chain_pll *new = malloc(sizeof(struct chain_pll));
    new->item = chain;
    new->next = tl->chains[frame];
    tl->chains[frame] = new;
}


struct chain_pll *tl_recall(struct chain_pll *c, id_type id) {
    if (c && c->item->id != id) {
        for (struct chain_pll *ci = c; ci->next; ci = ci->next) {
            if (ci->next->item->id == id) {
                struct chain_pll *c_orig = c;
                c = ci->next;
                ci->next = c->next;
                c->next = c_orig;
                break;
            }
        }
    }
    return c;
}


struct sig *tl_exec(struct timeline *tl, struct ctx *ctx) {
    int orig_frames = ctx->frames;
    for (int i = ctx->frame; i < ctx-> frame + ctx->frames; ++i) {
        for (struct chain_pll *ci = tl->chains[i]; ci; ci = ci->next) {
            chain_exec(ci->item, ctx);
            // This is stupid. Make it a nested list? don't store all these null pointers that get skipped over.
            // Realistically this should be called in a loop so O(n) trigger lookup shouldn't be an issue.
            // Honestly need to rethink this entire fucntion 
            --ctx->frames;
        }
    }
    ctx->frames = orig_frames;
    return NULL;
} 
