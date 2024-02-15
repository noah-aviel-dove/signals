#pragma once

#include "sig.h"
#include "link.h"


struct link_spec {
    struct linkfs fs;
    const char[LINK_NAME_MAX + 1] name;
};


void links_init(void);


union linkf linkf_get(const char*, enum link_prototype);

