#include "data.h"

#include <assert.h>
#include <stdlib.h>

#include "list.h"
#include "sig.h"


struct data_entry {
    id_type id;
    struct sig data;
};


STRUCT_LIST(data_entry);


#define DATA_SIZE 1024


static struct data_entry_ll *DATA[DATA_SIZE];


struct data_entry_ll **data_list(id_type id) {
    return &DATA[id % DATA_SIZE];
}


struct sig data_get(id_type id) {
    for (struct data_entry_ll *li = *data_list(id); li; li = li->next) {
        struct data_entry entry = li->item;
        if (entry.id == id) {
            return entry.data;
        }
    }
    assert(0); 
}


void data_put(id_type id, struct sig data) {
    struct data_entry_ll *ln, **lp = data_list(id);
    for (struct data_entry_ll *li = *lp; li; li = li->next) {
        struct data_entry entry = li->item;
        if (entry.id == id) {
            sig_free(&entry.data);
            entry.data = data;
            return;
        }
    }
    ln = malloc(sizeof(struct data_entry_ll));
    ln->item = (struct data_entry){.id = id, .data = data};
    ln->next = *lp;
    *lp = ln;
}


sca *data_get_scalar(id_type id) {
    struct sig s = data_get(id);
    assert(s.type == SIG_S);
    return s.val.s;
}


struct vec *data_get_vec(id_type id) {
    struct sig s = data_get(id);
    assert(s.type == SIG_V);
    return s.val.v;
}


struct buf *data_get_buf(id_type id) {
    struct sig s = data_get(id);
    assert(s.type == SIG_B);
    return s.val.b;
}


void data_put_sca(id_type id, sca *s) {
    data_put(id, (struct sig){SIG_S, {.s = s}});
}


void data_put_vec(id_type id, struct vec *v) {
    data_put(id, (struct sig){SIG_V, {.v = v}});
}


void data_put_buf(id_type id, struct buf *b) {
    data_put(id, (struct sig){SIG_B, {.b = b}});
}


void data_rm(id_type id) {
    for (struct data_entry_ll **lip = data_list(id); *lip; lip = &((*lip)->next)) {
        struct data_entry_ll li = **lip;
        struct data_entry entry = li.item;
        if (entry.id == id) {
            sig_free(&entry.data);
            *lip = li.next;
            free(lip);
            return;
        }
    }
    assert(0);
}
