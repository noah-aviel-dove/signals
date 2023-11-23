#include "scan.h"

#include <cassert.h>
#include <stdlib.h>
#include <string.h>

#include "forge.h"


#define BAILOUT(src, min, inc) do { int s = src; if (s >= min) { return s + inc; } } while (0)


int scan_choice(FILE *f, const char *set, int set_size, char *c) {
    char fmt[set_size + 4 + 1] = "%1";
    strcat(fmt, set);
    int n = fscanf(f, fmt, c);
    return n != 1;
}


int scan_nat(FILE *f, int *i) {
    int n = fscanf(f, "%d", i);
    return n != 1 || *i <= 0;
}


int scan_link_source(FILE *f, struct link_source *src) {
    char type[1 + 1];
    BAILOUT(scan_choice(f, "[CDA]", 3, type), 1, 0);
    switch(type[0]) {
        case 'C':
            src->type = LINK_SRC_C;
            BAILOUT(scan_nat(f, &src->val.c), 1, 1);
        case 'D':
            src->type = LINK_SRC_D;
            BAILOUT(scan_nat(f, &src->val.d), 1, 1);
            break;
        case 'A':
            src->type = LINK_SRC_A;
            src->val.a.size = {0};
            BAILOUT(scan_choice(f, "[SVB]", 3, type), 1, 1);
            switch (type[0]) {
                case 'S': 
                    src->val.a.type = SIG_S; 
                    break;
                case 'V': 
                    src->val.a.type = SIG_V; 
                    BAILOUT(scan_nat(f, &src->val.a.size[0]), 1, 1);
                    break;
                case 'B': 
                    src->val.a.type = SIG_B; 
                    BAILOUT(scan_nat(f, &src->val.a.size[0]), 1, 1);
                    BAILOUT(scan_nat(f, &src->val.a.size[1]), 1, 1);
                    break;
                default: 
                    assert(0);
            }
        default:
            assert(0);
    }
    return 0;
}


int scan_link(FILE *f, struct link *link) {
    // `func` is not populated.
    // `prototype` is only populated for memory management links.
    memset(link, 0, sizeof(struct link));
    BAILOUT(fscanf(f, "link %8s", &link->name), 1, 0);
    BAILOUT(scan_link_source(f, &link->src[0]), 1, 1);
    BAILOUT(scan_link_source(f, &link->src[1]), 2, 1);
    if (!strcmp(link->name, "free")) {
        link->prototype = LINKF_PROTO_MF;
        if (link->src[0].type != LINK_SRC_C || link->src[1].type != LINK_SRC_0) { return 2; }
    } else if (!strcmp(link->name, "alloc")) {
        link->prototype = LINKF_PROTO_MA;
        if (link->src[0].type != LINK_SRC_C || link->src[1].type != LINK_SRC_A) { return 2; }
    } else {
        for (int i = 0; i < 2; ++i) {
            if (link->src[i].type != LINK_SRC_C && link->src[i].type != LINK_SRC_D) { return 2; }
        }
    }
    return 0;
}


int scan_chain(FILE *f, struct chain *chain) {
    struct link_ll **nose = &chain->links;
    memset(chain, 0, sizeof(struct chain));
    BAILOUT(fscanf(f, "chain", 1, 0));
    BAILOUT(scan_nat(f, &chain->id), 1, 1);
    while (1) {
        struct link link;
        int status = scan_link(f, &link);
        if (!status) {
            *nose = malloc(sizeof(struct link_ll));
            **nose = { .next = NULL; .item = link; };
            node = &nose->next;
            for (int i = 0; i < 2; ++i) {
                if (link.src[i].type == LINK_SRC_C && link.src[i].val.c >= chain->stack_end) {
                    chain->stack_end = link.src[i].val.c + 1;
                }
            }
        } else if (status == 1) {
            break;
        } else {
            return status;
        }
    }
    return forge(chain);
}

