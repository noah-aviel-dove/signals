#if !defined(LINK_F) || !defined(LINK_FNAME)
#error
#endif

void link_##LINK_FNAME##_2b (struct buf *sig, struct buf *mod, id_type link_id, int frame) {
    assert(sig->frames == mod->frames);
    size_t sig_s = buf_size(sig), mod_s = buf_size(mod);
    if (sig_s > mod_s) {
        for (size_t i = 0; i < sig_s; i += 1) {
            LINK_F(sig->data[i], mod->data[i % mod_s]);
        }
    } else if (mod_s < sig_s) {
        for (size_t i = 0; i < mod_s; i += 1) {
            LINK_F(sig->data[i % sig_s], mod->data[i]);
        }
    } else {
        for (size_t i = 0; i < sig_s; i += 1) {
            LINK_F(sig->data[i], mod->data[i]);
        }
    }
}
