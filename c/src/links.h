#pragma once

#include "sig.h"
#include "link.h"


enum link_type {
    LINK_BCLOCK,
    LINK_GCLOCK,
    LINK_ISINE,
    LINK_NOISE,
    LINK_ADD2,
    LINK_MUL2
};


union linkf linkf_get(enum link_type);


void link_bclock(struct ctx*, struct buf*);


void link_gclock(struct ctx*, struct buf*);


void link_isine(struct ctx*, struct buf*);


void link_noise(struct ctx*, struct buf*);


void link_add2(struct ctx*, struct buf*, struct buf*);


void link_mul_bb(struct ctx*, struct buf*, struct buf*);


void link_mul_bs(struct ctx*, struct buf*, sca*);

