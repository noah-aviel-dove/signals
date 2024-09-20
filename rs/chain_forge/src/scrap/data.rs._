use std::collections::{HashMap, HashSet};

use crate::signal::Signal;

pub struct DataStore {
    data: HashMap<u64, DataEntry>,
}

struct DataEntry {
    value: Signal,
    refs: HashSet<u64>,
}

impl DataEntry {
    pub fn new(value: Signal) -> Self {
        Self {value, HashSet<_>::new()}
    }
    
    pub fn value(&self) {
        self.value
    }

    pub fn update(&mut self, value: Signal) {
        self.value = value;
        // Notify refs
    }
}

impl DataStore {
    pub fn new() -> Self {
        Self {HashMap::new()}
    }

    pub fn put(&mut self, id: u64, sig: Signal) -> bool {
        match self.data.entry(id) {
            Vacant(entry) => {
                entry.insert(DataEntry::new(value));
                false
            },
            Occupied(entry) => {
                entry.value = sig;
                entry.notify()
                true
            },

        }

        entry.and_modify(|entry| *entry.sig = sig).or_insert_with()
            None => false,
            Some(entry) => {
                for 
                true
            }
        }
    }
}
