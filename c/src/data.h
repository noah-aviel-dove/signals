#pragma once

#include "sig.h"


typedef int id_type;


struct sig data_get(id_type);

void data_put(id_type, struct sig);

sca *data_get_sca(id_type);

struct vec *data_get_vec(id_type);

struct buf *data_get_buf(id_type);

void data_put_sca(id_type, sca*);

void data_put_vec(id_type, struct vec*);

void data_put_buf(id_type, struct buf*);

void data_rm(id_type);

