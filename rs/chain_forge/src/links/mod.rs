mod osc;

use std::collection::HashMap;

use crate::link::LinkDef;

use crate::links::osc::{sin};


pub struct LinkLib {
    fns_by_name: HashMap<String, LinkDef>,
}

impl <'a> LinkLib {
    fn get_def(&self, name: &str) -> Option<&'a LinkDef> {
        self.fns_by_name.get(name)
    }

    fn new () -> Self {
        Self {
            fns_by_name: HashMap::from([
                (),

            ])
        }
    }
}

