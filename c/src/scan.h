#pragma once

#include <stdio.h>

#include "chain.h"
#include "link.h"


/*
 * Return value means:
 * 0: success
 * 1: failure, only whitespace consumed
 * >1: failure, some non-whitespace consumed
 * */

int scan_choice(FILE*, const char*, int, char*);


int scan_nat(FILE*, int*);


int scan_link_source(FILE *, struct link_source*);


int scan_link(FILE*, struct link*);


int scan_chain(FILE *f, struct chain*);
