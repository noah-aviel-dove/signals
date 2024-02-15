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
        sca *s; 
        struct vec *v;
        struct buf *b;
    };
};


struct sig_alloc_args {
    enum sig_type type;
    int size[2];
};


/* 
 * Lifecycle management
 */
struct sig_alloc_args sig_args(struct sig*);


void sig_alloc(struct sig*, struct sig_alloc_args);


sca *sca_alloc(void);


struct vec *vec_alloc(int);


struct buf *buf_alloc(int, int);


void sig_free(struct sig*);


/*
 * Conversion
 */
void vtos(struct sig*, struct sig*);


void btos(struct sig*, struct sig*);


void stov(struct sig*, struct sig*);


void btov(struct sig*, struct sig*);


void stob(struct sig*, struct sig*);


void vtob(struct sig*, struct sig*);


/*
 * Other
 */
int buf_size(struct buf*);

