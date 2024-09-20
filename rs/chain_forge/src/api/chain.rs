use crate::chain::{Chain, ChainSpec};
use crate::link::LinkSpec;
use crate::signal::Signal;
use crate::Id;
use std::collections::HashMap;

pub struct ChainApi {
    mesh: HashMap<Id, Chain>,
}

impl<'a> ChainApi {
    pub fn new() -> Self {
        Self {
            mesh: HashMap::<_, _>::new(),
        }
    }

    pub fn list(&self) -> Vec<Id> {
        self.mesh.keys().copied().collect::<Vec<_>>()
    }

    pub fn get(&self, id: Id) -> Option<ChainSpec> {
        let chain = self.mesh.get(&id)?;
        Some(chain.describe())
    }

    pub fn put(&mut self, id: Id, spec: ChainSpec) -> bool {
        let chain = spec.reify();
        self.mesh.insert(id, chain).is_some()
    }

    pub fn del(&mut self, id: Id) -> bool {
        self.mesh.remove(&id).is_some()
    }

    pub fn get_links(&self, id: Id) -> Option<Vec<LinkSpec>> {
        let chain = self.mesh.get(&id)?;
        Some(chain.describe_links())
    }

    pub fn get_link(&self, id: Id, index: usize) -> Option<LinkSpec> {
        let link: &_ = self.mesh.get(&id)?.links.get(index)?;
        Some(link.describe())
    }

    pub fn get_vars(&'a self, id: Id) -> Option<&'a Vec<Signal>> {
        let chain = self.mesh.get(&id)?;
        Some(&chain.vars)
    }

    pub fn get_var(&'a self, id: Id, index: usize) -> Option<&'a Signal> {
        let var = self.mesh.get(&id)?.vars.get(index)?;
        Some(&var)
    }

    pub fn patch_var(
        &mut self,
        id: Id,
        index: usize,
        new_var: Signal,
    ) -> Option<Result<(), String>> {
        let var = self.mesh.get_mut(&id)?.vars.get_mut(index)?;
        let old_spec = var.describe();
        let new_spec = new_var.describe();
        if old_spec == new_spec {
            *var = new_var;
            Some(Ok(()))
        } else {
            Some(Err(format!("Cannot patch {old_spec} with {new_spec}")))
        }
    }
}
