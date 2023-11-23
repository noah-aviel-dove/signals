#pragma once

#include "sig.h"
#include "link.h"



union linkf linkf_get(const char[8], enum link_prototype);


void link_bclock(struct ctx*, struct buf*);


void link_gclock(struct ctx*, struct buf*);


void link_isine(struct ctx*, struct buf*);


void link_noise(struct ctx*, struct buf*);


void link_add2(struct ctx*, struct buf*, struct buf*);


void link_mul_bb(struct ctx*, struct buf*, struct buf*);


void link_mul_bs(struct ctx*, struct buf*, sca*);

