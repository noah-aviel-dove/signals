#if !defined(LINK_F) || !defined(LINK_FNAME)
#error
#endif

void link_##LINK_FNAME##_1b1s(struct buf *sig, struct buf *mod, id_type link_id, int frame) {
    sig scalar = data_get_scalar(link_id);
    size_t s = buf_size(sig);
    for (size_t i = 0; i < s; i += 1) {
        LINK_F(sig->data[i], scalar, i);
    }
}
