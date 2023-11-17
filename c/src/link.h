#pragma once

#include <stdbool.h>

#include "data.h"
#include "list.h"
#include "sig.h"


struct chain;


typedef int stack_index;


struct ctx {
    int frame, frames, rate;
    unsigned int seed;
    bool stop;
};


enum link_prototype {
    /* MA := Memory allocation function
     * MF := Memory freeing function
     * S  := sca(lar)
     * V  := vec(tor)
     * B  := buf(fer)
     * E  := arguments have equal numbers of channels
     * 1F := 1st argument has fewer channels
     * 1M := 1st argument has more channels
     * */
    LINK_PROTO_MA,
    LINK_PROTO_MF,
    LINK_PROTO_S,
    LINK_PROTO_V,
    LINK_PROTO_B,
    LINK_PROTO_SS,
    LINK_PROTO_VS,
    LINK_PROTO_VV_E,
    LINK_PROTO_VV_1F,
    LINK_PROTO_VV_1M,
    LINK_PROTO_BS,
    LINK_PROTO_BV_E,
    LINK_PROTO_BV_1F,
    LINK_PROTO_BV_1M,
    LINK_PROTO_BB_E,
    LINK_PROTO_BB_1F,
    LINK_PROTO_BB_1M
};


typedef void (*linkf_s )(struct ctx*, sca*                    );
typedef void (*linkf_v )(struct ctx*, struct vec*             );
typedef void (*linkf_b )(struct ctx*, struct buf*             );
typedef void (*linkf_ss)(struct ctx*, sca*       , sca*       );
typedef void (*linkf_vs)(struct ctx*, struct vec*, sca*       );
typedef void (*linkf_vv)(struct ctx*, struct vec*, struct vec*);
typedef void (*linkf_bs)(struct ctx*, struct buf*, sca*       );
typedef void (*linkf_bv)(struct ctx*, struct buf*, struct vec*);
typedef void (*linkf_bb)(struct ctx*, struct buf*, struct buf*);


union linkf {
    char m; // Not accessed

    linkf_s s;
    linkf_v v;
    linkf_b b;
    linkf_ss ss;
    linkf_vs vs;
    linkf_vv vv_e, vv_1f, vv_1m; 
    linkf_bs bs;
    linkf_bv bv_e, bv_1f, bv_1m;
    linkf_bb bb_e, bb_1f, bb_1m;
};


enum link_source_type {
    /* C := Chain stack
     * D := Data store
     * A := Memory allocation parameters
     * 1 := 1st argument (mandatory)
     * 2 := 2nd argument (optional)
     * */
    LINK_SRC_C1 = 1 << 0,
    LINK_SRC_D1 = 1 << 1,
    LINK_SRC_C2 = 1 << 2,
    LINK_SRC_D2 = 1 << 3,
    LINK_SRC_A2 = 1 << 4,
};


union link_source {
    id_type d;
    stack_index c;
    struct sig_alloc_info *a;
};


struct link {
    enum link_prototype prototype;
    enum link_source_type src_type;
    union link_source src[2];
    union linkf func;
};


STRUCT_LIST(link);
STRUCT_PLIST(link);


void link_exec(struct ctx*, struct chain*, struct link*);


struct link link_alloc(stack_index, struct sig_alloc_info*);


struct link link_free(stack_index);

