#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "data.h"
#include "list.h"
#include "sig.h"


struct chain;


typedef int32_t chain_stack_index;


struct ctx {
    int frame, frames, rate;
    unsigned int seed;
    bool stop;
};


enum link_dim_cmp {
    DIM_CMP_0  = 0,
    DIM_CMP_EQ,
    DIM_CMP_1L,
    DIM_CMP_1G
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
    LINK_PROTO_0        = 0x00,
    LINK_PROTO_MA       = 0x01, 
    LINK_PROTO_MF       = 0x02,
    LINK_PROTO_S        = SIG_S << 4,
    LINK_PROTO_V        = SIG_V << 4,
    LINK_PROTO_B        = SIG_B << 4,
    LINK_PROTO_SS       = SIG_S << 4 | SIG_S << 8,
    LINK_PROTO_VS       = SIG_V << 4 | SIG_S << 8,
    LINK_PROTO_VV_EQ    = SIG_V << 4 | SIG_V << 8 | DIM_CMP_EQ << 12,
    LINK_PROTO_VV_1L    = SIG_V << 4 | SIG_V << 8 | DIM_CMP_1L << 12,
    LINK_PROTO_VV_1G    = SIG_V << 4 | SIG_V << 8 | DIM_CMP_1G << 12,
    LINK_PROTO_BS       = SIG_B << 4 | SIG_S << 8,
    LINK_PROTO_BV_E     = SIG_B << 4 | SIG_V << 8 | DIM_CMP_EQ << 12,
    LINK_PROTO_BV_1L    = SIG_B << 4 | SIG_V << 8 | DIM_CMP_1L << 12;
    LINK_PROTO_BV_1G    = SIG_B << 4 | SIG_V << 8 | DIM_CMP_1G << 12;
    LINK_PROTO_BB_EQ    = SIG_B << 4 | SIG_B << 8 | DIM_CMP_EQ << 12;
    LINK_PROTO_BB_1L    = SIG_B << 4 | SIG_B << 8 | DIM_CMP_1L << 12;
    LINK_PROTO_BB_1G    = SIG_B << 4 | SIG_B << 8 | DIM_CMP_1G << 12;
};


typedef void (*linkf_0 )(void                                 );
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
    linkf_0 NOT_USED;
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
     * */
    LINK_SRC_0 = 0,
    LINK_SRC_C,
    LINK_SRC_D,
    LINK_SRC_MA,
    LINK_SRC_MF
};


enum link_source_type merge(enum link_source_type, enum_link_source_type);


union link_source_info {
    id_type d;
    chain_stack_index c;
    struct sig_alloc_info a;
};


struct link_source {
    union link_source_info val;
    enum link_source_type type;
};


#define LINK_MAX_NAME_SIZE 8

struct link {
    enum link_prototype prototype;
    struct link_source src[2];
    char fname[LINKF_NAME_MAX + 1];
    union linkf func;
};


STRUCT_LIST(link);
STRUCT_PLIST(link);


void link_exec(struct ctx*, struct chain*, struct link*);


struct link link_alloc(chain_stack_index, struct sig_alloc_info*);


struct link link_free(chain_stack_index);

