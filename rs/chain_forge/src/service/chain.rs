use serde::{Deserialize, Serialize};

use crate::signal::Signal;

#[derive(Serialize, Deserialize, Clone)]
struct LinkArg {
    pub persistent: bool,
    pub index: usize,
}

pub struct Link {
    fname: String,
    func: (),
    args: Vec<LinkArg>,
}

pub struct Chain {
    pub links: Vec<Link>,
    pub vars: Vec<Signal>,
    pub stack: Vec<Signal>,
}

impl Link {
    pub fn describe(&self) -> spec::LinkSpec {
        spec::LinkSpec {
            fname: self.fname.clone(),
            args: self.args.clone(),
        }
    }
}

impl Chain {
    pub fn describe(&self) -> spec::ChainSpec {
        spec::ChainSpec {
            vars: self.vars.clone(),
            links: self.describe_links(),
        }
    }

    pub fn describe_links(&self) -> Vec<spec::LinkSpec> {
        self.links.iter().map(|link| link.describe()).collect()
    }
}

pub mod spec {
    use crate::service::chain::*;

    #[derive(Serialize, Deserialize)]
    pub struct LinkSpec {
        pub fname: String,
        pub args: Vec<LinkArg>,
    }

    #[derive(Serialize, Deserialize)]
    pub struct ChainSpec {
        pub links: Vec<LinkSpec>,
        pub vars: Vec<Signal>,
    }

    impl LinkSpec {
        pub fn reify(self) -> Link {
            Link {
                fname: self.fname,
                args: self.args,
                func: (),
            }
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
}
