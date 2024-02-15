#pragma once

#include "sig.h"
#include "map.h"


void data_init(void);


// TODO remove asserts, give caller control over error handling
void data_get(key_t, struct sig*);

void data_put(key_t, struct sig*);

sca *data_get_scalar(key_t);

struct vec *data_get_vec(key_t);

struct buf *data_get_buf(key_t);

void data_put_sca(key_t, sca*);

void data_put_vec(key_t, struct vec*);

void data_put_buf(key_t, struct buf*);

void data_rm(key_t);

