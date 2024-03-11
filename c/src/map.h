#pragma once

#include <stdalign.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>

#include "list.h"


typedef uint64_t key_t;


struct map_item {
    key_t key;
    /* This will only be created via `malloc` which always uses maximum alignment,
     * so all this does is add padding between `key` and `value`. 
     */
    alignas(max_align_t) char value[];
};


STRUCT_LIST(map_item);


struct map {
    size_t width, size, value_size;
    struct map_item_ll **data;
};


/*
 * Initialize a newly created map.
 *
 * 1: An unitialized map.
 * 2: The map's width. If the map's size is much greater than its width, performance will suffer. If the width is zero, the map cannot be used until a new width is set.
 * 3: The size in bytes of type of the values to be stored in the map.
 * */
void map_init(struct map*, size_t, size_t);


/*
 * Remove all items from the map.
 * 
 * 1: An initialized map.
 * 2: The new width of the map. If the new width is zero, the map itself is freed and cannot be used until `map_init` is called again.
 * */
void map_clear(struct map*, size_t);


/*
 * Copy the contents of one map to another, overwriting its contents if necessary.
 *
 * 1: The map to be written to. It must have been initialized.
 * 2: The map to be read from. It must have been intialized.
 * */
void map_copy(struct map*, struct map*);


/*
 * Retrieve a value from the map.
 *
 * 1: An initialized map.
 * 2: The associated key of the value to retrieve.
 * R: A pointer to the associated value, or NULL if they key was not found in the map. 
 *    The pointer may be written to, which will update the value stored in the map.
 *    The pointer is affected by subsequent changes to the map, and will become a dangling pointer if the value is removed from the map.
 * */
void *map_get(struct map*, key_t);


/*
 * Insert a new key and value into the map, overwriting and retrieving any existing value associated with the given key.
 *
 * 1: An initialized map with positive width.
 * 2: The key of the new entry.
 * 3: A pointer to the key's associated value (must be readable to at least `map->value_size` bytes).
 * 4: A pointer to store any previous value associated with the given key. Must be writable to at least `map->value_size` bytes, or NULL.
 * R: Whether the given key was already present in the map. If $4 is not NULL, this indicates that it was written to.
 * */
bool map_put(struct map*, key_t, void*, void*);


/*
 * Insert a new key and value into the map, unless the key is already present.
 *
 * 1: An initialized map with positive width.
 * 2: The key of the new entry.
 * 3: A pointer to the key's associated value (must be readable to at least `map->value_size` bytes).
 * R: A pointer to the value associated with the given key if the key was already present in the map, or NULL if it wasn't. 
 * */
void *map_submit(struct map*, key_t, void*);


/*
 * Retrieve and remove a value from the map.
 *
 * 1: An initialized map.
 * 2: The key associated with the value to remove.
 * 3: A pointer to store the value associated with the given key. Must be writable to at least `map->value_size` bytes, or NULL.
 * R: Whether the key was found within the map.
 * */
bool map_pop(struct map*, key_t, void*);


/*
 * Change the map's width.
 *
 * 1: An initialized map.
 * 2: The map's new width. If either but both of the map's previous width and its new width are zero, errors or memory leaks may occur.
 * */
void map_redistribute(struct map*, size_t);


/*
 * Write the contents of the map to a file. The map's values are shown in hexadecimal.
 *
 * 1: A writable file.
 * 2: An initialized map.
 * */
void map_print(FILE*, struct map*);


// See if we can make visitor variadic to faciliate partial application,
// e.g. `map_visit(m, func, a, b)` where `func(struct map_item, struct map_status*, typeof(a), typeof(b))`
void map_visit(struct map*, void *(*)(struct map_item));




