use serde::{Deserialize, Serialize};

use crate::link::{Link, LinkSpec};
use crate::signal::Signal;

pub struct Chain {
    pub links: Vec<Link>,
    pub vars: Vec<Signal>,
    pub stack: Vec<Signal>,
}

#[derive(Serialize, Deserialize)]
pub struct ChainSpec {
    pub links: Vec<LinkSpec>,
    pub vars: Vec<Signal>,
}

impl Chain {
    pub fn describe(&self) -> ChainSpec {
        ChainSpec {
            vars: self.vars.clone(),
            links: self.describe_links(),
        }
    }

    pub fn describe_links(&self) -> Vec<LinkSpec> {
        self.links.iter().map(|link| link.describe()).collect()
    }
}

impl ChainSpec {
    pub fn reify(self) -> Chain {
        Chain {
            links: self.links.into_iter().map(|spec| spec.reify()).collect(),
            vars: self.vars,
            stack: Vec::new(),
        }
    }
}
