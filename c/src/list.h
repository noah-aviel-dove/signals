#pragma once

#define LIST(item_type)         struct item_type##_ll  {         item_type  item; struct item_type##_ll  *next; }
#define PLIST(item_type)        struct item_type##_pll {         item_type *item; struct item_type##_pll *next; }
#define ENUM_LIST(item_type)    struct item_type##_ll  { enum    item_type  item; struct item_type##_ll  *next; }
#define ENUM_PLIST(item_type)   struct item_type##_pll { enum    item_type *item; struct item_type##_pll *next; }
#define STRUCT_LIST(item_type)  struct item_type##_ll  { struct  item_type  item; struct item_type##_ll  *next; }
#define STRUCT_PLIST(item_type) struct item_type##_pll { struct  item_type *item; struct item_type##_pll *next; }
#define UNION_LIST(item_type)   struct item_type##_ll  { union   item_type  item; struct item_type##_ll  *next; }
#define UNION_PLIST(item_type)  struct item_type##_pll { union   item_type *item; struct item_type##_pll *next; }

