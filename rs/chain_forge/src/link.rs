use serde::{Deserialize, Serialize};

use crate::chain::Chain;

use crate::signal::{Signal, SignalKind};

pub struct Context {
    pub position: usize,
    pub size: usize,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct LinkArg {
    pub persistent: bool,
    pub index: usize,
}

#[derive(Serialize, Deserialize, Clone)]
struct LinkDef {
    pub name: String,
    pub bounds: Vec<SignalKind>,
}

#[derive(Serialize, Deserialize, Clone)]
pub struct LinkSpec {
    pub name: String,
    pub args: Vec<LinkArg>,
}


type UnaryLinkFn = fn(&Context, &mut Signal) -> ()
type BinaryLinkFn = fn(&Context, &mut Signal, &mut Signal) -> ()


fn exec_null(context: &Context, chain: &mut Chain, link: &Link) {
    assert_eq!(0, link.spec.args.len());
    link.func(context);
}

fn exec_un(context: &Context, chain: &mut Chain, link: &Link) {
    assert_eq!(1, link.spec.args.len());
    let arg0 = link.spec.args[0];
    let sig0 = arg0.load(chain);
    link.func(sig0)
}

pub struct Link <'a> {
    pub def: &'a LinkDef,
    pub args: Vec<LinkArg>,
}

impl Link {
    pub fn describe(&self) -> LinkSpec {
        LinkSpec {
            name: self.def.name.clone(),
            args: self.args.clone(),
        }
    }

    pub fn exec(&self, chain: &mut Chain, context: &Context) {}
}

impl LinkSpec {
    pub fn reify(self) -> Link {
        Link {
            ,
            func: (),
        }
    }
}


impl<'a> LinkArg {
    pub fn load(&self, chain: &'a mut Chain) -> &'a mut Signal {
        let source = if self.persistent {
            &mut chain.vars
        } else {
            &mut chain.stack
        };
        source
            .get_mut(self.index)
            .expect("Link argument indices should be pre-validated")
    }
}
