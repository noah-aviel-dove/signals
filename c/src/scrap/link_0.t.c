#if !defined(LINK_F) || !defined(LINK_FNAME)
#error
#endif

void link_##LINK_FNAME##_0(struct buf *sig, struct buf *mod, id_type link_id, int frame) {
    size_t s = buf_size(sig);
    for (size_t i = 0; i < n; i +=1) { 
        LINK_F(out->data[i], i);
    }
}
