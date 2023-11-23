#pragma once

#include <stdlib.h>

#include "list.h"


typedef float sca;


struct vec {
    int size;
    sca data[];
};


struct buf {
    int channels;
    int frames;
    sca data[];
};


enum sig_type {
    SIG_0, //Indicates NULL or uninitilaized
    SIG_S,
    SIG_V,
    SIG_B,
};


struct sig {
    enum sig_type type;
    union {
        sca *s; // Does this have to be a pointer? If so, explain why here.
        struct vec *v;
        struct buf *b;
    } val;
};


struct sig_alloc_info {
    enum sig_type type;
    int size[2];
};


void sig_alloc(struct sig*, struct sig_alloc_info);


struct vec *vec_alloc(int);


struct buf *buf_alloc(int, int);


void sig_free(struct sig*);


int buf_size(struct buf*);

