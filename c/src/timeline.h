#pragma once

#include <stdlib.h>

#include "sig.h"
#include "chain.h"


struct timeline {
    int frames;
    struct chain_pll **chains;
};


void tl_init(struct timeline*, int);


// Does not free the referenced chains, only the tl scaffolding
void tl_free(struct timeline*);


void tl_add(struct timeline*, int, struct chain*); 


// Search a list for a chain and move it to the front if it's found
struct chain_pll *tl_recall(struct chain_pll*, id_type);


struct chain *tl_pop(struct chain_pll*, id_type);


struct sig *tl_exec(struct timeline*, struct ctx*);

