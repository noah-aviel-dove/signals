#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>

#include "chain.h"
#include "data.h"
#include "link.h"


struct link alloc_link(void);
struct link mul_link(void);
struct link clock_link(void);
struct link sine_link(void);

void dump_buf(struct buf*, const char*);

#define BLOCK_SIZE 400
#define CHANNEL_COUNT 2
#define STACK_SIZE 1
#define FRAME_RATE 44100

#define FRAMERATE_DATA_ID 1

int main(void) {
    
    struct link_ll sine_node  = {.item = sine_link(),  .next = NULL};
    struct link_ll mul_node   = {.item = mul_link(),   .next = &sine_node};
    struct link_ll clock_node = {.item = clock_link(), .next = &mul_node};
    struct link_ll alloc_node = {.item = alloc_link(), .next = &clock_node};

    struct chain the_chain = {
        .id = 1,
        .max_stack_size = STACK_SIZE,
        .links = &alloc_node
    };

    struct ctx ctx = {
        .frame = 0, 
        .frames = BLOCK_SIZE, 
        .rate = FRAME_RATE,
        .seed = 0, 
        .stop = false
    };
    
    struct sig result;
    
    sca freqscale = 1.0/FRAME_RATE;
    // This is totally uncecessary, only doing it to test the data store
    data_put_sca(FRAMERATE_DATA_ID, &freqscale);
   
    chain_init(&the_chain);
    chain_exec(&the_chain, &ctx);
    result = *(chain->stack);
    assert(result.type == SIG_B);
    
    dump_buf(result.val.b, "sine_out.txt");

    return 0;
}


struct link alloc_link(void) {
    struct sig_alloc_info *ai = malloc(sizeof(struct sig_alloc_info) + sizeof ai->size[0] * 2);
    ai->type = SIG_B;
    ai->size[0] = CHANNEL_COUNT;
    ai->size[1] = BLOCK_SIZE;
    return link_alloc(RESULT_INDEX, ai);
}

struct link clock_link(void) {
    return (struct link) {
        .prototype = LINK_PROTO_B,
        .src_type = LINK_SRC_C1,
        .src = {{.c = RESULT_INDEX}},
        .func = {.b = &link_gclock}
    };
}

struct link mul_link(void) {
    return (struct link) {
        .prototype = LINK_PROTO_BS,
        .src_type = LINK_SRC_C1 | LINK_SRC_D2,
        .src = {{.c = RESULT_INDEX}, {.d = FRAMERATE_DATA_ID}},
        .func = {.bs = &link_mul_bs}
    };
}

struct link sine_link(void) {
    return (struct link) {
        .prototype = LINK_PROTO_B,
        .src_type = LINK_SRC_C1,
        .src = {{.c = RESULT_INDEX}},
        .func = {.b = &link_isine}
    };
}

void dump_buf(struct buf *b, const char *fname) {
    FILE *f = fopen(fname, "w");
    fprintf(f, "%d\n%d\n", b->channels, b->frames);
    for (int i = 0; i < b->channels; ++i) {
        for (int j = 0; j < b->frames; ++j) {
            fprintf(f, "%f ", b->data[i * b->frames + j]);
        }
        fprintf(f, "\n");
    }
    fclose(f);
}

