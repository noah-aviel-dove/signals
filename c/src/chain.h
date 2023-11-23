#pragma once

#include <stdlib.h>

#include "sig.h"
#include "link.h"
#include "list.h"


struct chain {
    id_type id;
    chain_stack_index stack_end;
    struct sig *stack;
    struct link_ll *links;
};

STRUCT_LIST(chain);
STRUCT_PLIST(chain);


struct sig chain_exec(struct chain*, struct ctx*);

