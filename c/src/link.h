#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "data.h"
#include "list.h"
#include "sig.h"


typedef int chain_stack_index;


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

#define LINK_MAX_ARITY 2;


// this might no longer be needed
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
    LINK_PROTO_BV_EQ    = SIG_B << 4 | SIG_V << 8 | DIM_CMP_EQ << 12,
    LINK_PROTO_BV_1L    = SIG_B << 4 | SIG_V << 8 | DIM_CMP_1L << 12,
    LINK_PROTO_BV_1G    = SIG_B << 4 | SIG_V << 8 | DIM_CMP_1G << 12,
    LINK_PROTO_BB_EQ    = SIG_B << 4 | SIG_B << 8 | DIM_CMP_EQ << 12,
    LINK_PROTO_BB_1L    = SIG_B << 4 | SIG_B << 8 | DIM_CMP_1L << 12,
    LINK_PROTO_BB_1G    = SIG_B << 4 | SIG_B << 8 | DIM_CMP_1G << 12
};


enum link_param_prototype {
    LINK_PROT0_0 = SIG_0,
    LINK_PROTO_S = SIG_S,
    LINK_PROTO_V = SIG_V,
    LINK_PROTO_B = SIG_B,
    LINK_PROTO_M
};


typedef uint32_t linkf_prototype;


typedef void (*linkf_0 )(struct ctx*,                         );
typedef void (*linkf_s )(struct ctx*, sca*                    );
typedef void (*linkf_v )(struct ctx*, struct vec*             );
typedef void (*linkf_b )(struct ctx*, struct buf*             );
typedef void (*linkf_ss)(struct ctx*, sca*       , sca*       );
typedef void (*linkf_vs)(struct ctx*, struct vec*, sca*       );
typedef void (*linkf_vv)(struct ctx*, struct vec*, struct vec*);
typedef void (*linkf_bs)(struct ctx*, struct buf*, sca*       );
typedef void (*linkf_bv)(struct ctx*, struct buf*, struct vec*);
typedef void (*linkf_bb)(struct ctx*, struct buf*, struct buf*);


struct linkfs {
    linkf_0 _0;
    linkf_s s;
    linkf_v v;
    linkf_b b;
    linkf_ss ss;
    linkf_vs vs;   
    linkf_vv vv_eq, vv_1l, vv_1g;
    linkf_bs bs;   
    linkf_bv bv_eq, bv_1l, bv_1g;
    linkf_bb bb_eq, bb_1l, bb_1g;
};


union link_name {
    key_t key;
    char str[sizeof(key_t) + 1];
};


struct link_spec {
    struct linkfs fs;
    int arity;
    union link_name name;
};


enum link_arg_source_type {
    LINK_SRC_0, // No argument
    LINK_SRC_C, // Chain stack index
    LINK_SRC_D, // Data store key
    LINK_SRC_M, // Memory allocation literal
};


struct link_arg_source {
    enum link_arg_source_type type;
    union {
        key_t data_key;
        chain_stack_index stack_index;
        struct sig_alloc_args alloc_args;
    };
};

struct link_dispatch {
    union {
        link_0 _0;
        linkf_s s;
        linkf_v v;
        linkf_b b;
        linkf_ss ss;
        linkf_vs vs;
        linkf_vv vv;
        linkf_bs bs;
        linkf_bv bv;
        linkf_bb b
    } func;
    linkf_prototype prototype;
    struct sig *args[LINK_MAX_ARITY];
};

struct link {
    struct link_spec *spec;
    struct link_arg_source sources[LINK_MAX_ARITY];
    struct link_dispatch *dispatch;
};


STRUCT_LIST(link);
STRUCT_PLIST(link);


void link_exec(struct ctx*, struct link*);


// Move these elsewhere and rename
struct link link_alloc(chain_stack_index, struct sig_alloc_info);


struct link link_free(chain_stack_index);

