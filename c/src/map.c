#include "map.h"

#include <string.h>


size_t map_lane_index(size_t, key_t);


struct map_item_ll **map_lane(struct map*, key_t);


void map_init(struct map *map, size_t width, size_t value_size) {
    map->value_size = value_size;
    map->width = width;
    map->size = 0;
    map->data = calloc(map->width, sizeof map->data[0]);
}


void map_clear(struct map *map, size_t width) {
    for (size_t i = 0; i < map->width; ++i) {
        for (struct map_item_ll *node = map->data[i]; node;) {
            struct map_item_ll *next = node->next;
            free(node);
            node = next;
        }
    }
    if (width) {
        if (width != map->width) {
            map->data = realloc(map->data, width * sizeof map->data[0]);
        }
        memset(map->data, 0, width * sizeof map->data[0]);
    } else {
        free(map->data);
        map->data = NULL;
    }
    map->width = width;
}


void map_copy(struct map *dst, struct map *src, size_t width) {
    if (!width) {
        width = src->width;
    }
    if (dst->data) {
        map_clear(dst, width);
        dst->value_size = map->value_size;
    } else {
        map_init(dst, src->value_size, width)
    }
    for (size_t i = 0; i < src->width; ++i) {
        for (struct map_item_ll *node = src->data[i]; node; node = node->next) {
            map_put(dst, node->item.key, node->item.value);
        }
    }
}


void *map_get(struct map *map, key_t key) {
    for (struct map_item_ll *node = *map_lane(map, key); node; node = node->next) { 
        if (node->item.key == key) {
            return &(node->item.value);
        }
    }
    return NULL;
}


bool map_put(struct map *map, key_t key, void *value, void *old_value) {
    struct map_item_ll **lane = map_lane(map, key);
    struct map_item_ll *found_node = NULL;
    bool found;
    for (struct map_item_ll *node = *lane; node; node = node->next) {
        if (node->item.key == key) {
            found_node = node;
            if (old_value) {
                memcpy(old_value, &(node->item.value), map->value_size);
            }
            break;
        }
    }
    found = !!found_node;
    if (!found) {
        // Relies on `item` being the last member of `*_ll`.
        found_node = malloc(sizeof(struct map_item_ll) + map->value_size);
        found_node->next = *lane;
        *lane = found_node;
        ++map->size;
    }
    found_node->item.key = key;
    memcpy(found_node->item.value, value, map->value_size);
    return found;
}


void *map_submit(struct map *map, key_t key, void *value) {
    struct map_item_ll **lane = map_lane(map, key);
    struct map_item_ll *new_node;
    for (struct map_item_ll *node = *lane; node; node = node->next) {
        if (node->item.key == key) {
            return &(node->item.value);
        }
    }
    // Relies on `item` being the last member of `*_ll`.
    new_node = malloc(sizeof(struct map_item_ll) + map->value_size);
    new_node->item.key = key;
    memcpy(new_node->item.value, value, map->value_size);
    new_node->next = *lane;
    *lane = new_node;
    ++map->size;
    return NULL;
}


bool map_pop(struct map *map, key_t key, void *value) {
    struct map_item_ll *node;
    for (struct map_item_ll **lane = map_lane(map, key); *lane; lane = &((*lane)->next)) {
        node = *lane;
        if (node->item.key == key) {
            if (value) {
                memcpy(value, &(node->item.value), map->value_size);
            }
            *lane = node->next;
            free(node);
            --map->size;
            return true;
        }
    }
    return false;
}


// See if we can make visitor variadic to faciliate partial application,
// e.g. `map_visit(m, func, a, b)` where `func(struct map_item, struct map_status*, typeof(a), typeof(b))`
void map_visit(struct map *map, void *(*visitor)(struct map_item)) {
    void *new_value;
    for (size_t i = 0; i < map->width; ++i) {
        for (struct map_item_ll *node = map->data[i]; node; node = node->next) {
            new_value = visitor(node->item);
            if (new_value) {
                memcpy(node->item.value, new_value, map->value_size);
            }
        }
    }
}


void map_redistribute(struct map *map, size_t width) {
    struct map_item_ll **new_data = calloc(width, sizeof map->data[0]);
    struct map_item_ll *next;
    size_t new_index;
    for (size_t i = 0; i < map->width; ++i) {
        for (struct map_item_ll *node = map->data[i]; node;) {
            next = node->next;
            new_index = map_lane_index(width, node->item.key);
            node->next = new_data[new_index];
            new_data[new_index] = node;
            node = next;
        }  
    }
    free(map->data);
    map->data = new_data;
    map->width = width;
}


void map_print(FILE *f, struct map *map) {
    char value_buf[map->value_size * 2 + 1];
    const char *item_prefix, *item_suffix;
    if (map->size <= 16) {
        item_prefix = "";
        item_suffix = ", ";
    } else {
        item_prefix = "\t";
        item_suffix = ",\n";
    }
    fputc('{', f);
    for (size_t i = 0; i < map->width; ++i) {
        for (struct map_item_ll *node = map->data[i]; node; node = node->next) {
            for (size_t j = 0; j < map->value_size; ++j) {
                sprintf(value_buf + j * 2, "%02x", node->item.value[j]);
            }
            fprintf(f, "%s%ld: 0x%s%s", item_prefix, node->item.key, value_buf, item_suffix);
        }
    }
    fputc('}', f);
}


size_t map_lane_index(size_t width, key_t key) {
    return (key % width) + ((key < 0) * width);
}


struct map_item_ll **map_lane(struct map *map, key_t key) {
    return &map->data[map_lane_index(map->width, key)];
}


