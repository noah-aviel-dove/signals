#pragma once

#define LIST(item_type)         struct item_type##_ll  { struct item_type##_ll  *next;        item_type  item; }
#define PLIST(item_type)        struct item_type##_pll { struct item_type##_pll *next;        item_type *item; }
#define ENUM_LIST(item_type)    struct item_type##_ll  { struct item_type##_ll  *next; enum   item_type  item; }
#define ENUM_PLIST(item_type)   struct item_type##_pll { struct item_type##_pll *next; enum   item_type *item; }
#define STRUCT_LIST(item_type)  struct item_type##_ll  { struct item_type##_ll  *next; struct item_type  item; }
#define STRUCT_PLIST(item_type) struct item_type##_pll { struct item_type##_pll *next; struct item_type *item; }
#define UNION_LIST(item_type)   struct item_type##_ll  { struct item_type##_ll  *next; union  item_type  item; }
#define UNION_PLIST(item_type)  struct item_type##_pll { struct item_type##_pll *next; union  item_type *item; }

