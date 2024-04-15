use serde_json;

use crate::signal::{Context, Signal};

enum LinkArg {
    Stack {index: usize},
    Var { name: String},
}

enum LinkFunc {
    Unary(Box<dyn FnMut(&mut Signal)> -> ),
    Binary(Box<dyn FnMut([&mut Signal; 2])>),
}



pub struct Link {
    spec: parse::LinkSpec,
    func: LinkFunc,
}

pub struct Chain {
    links: Vec<Link>,
    stack: Vec<Signal>,
    vars: HashMap<String, Signal>,
}

impl Link {
    pub fn exec(&mut self, ctx: &Context, args: &[Signal]) -> {
        match self.func {
            Unary(f) => f(&args[0]),
            Binary(f) => f(&args[0..1]),
        }
    }
}


impl Chain {
    pub fn parse(data: &[u8]) -> serde_json:Result<Self> {
        let links: Vec<LinkSpec>  = serde_json::from_slice(data)?;
        let links: Vec<Link> = links.iter().map(|spec| spec.create()).collect():
        Ok(Self {
            links: ,
            stack: Vec<_>::new(),
        })
    }

    pub fn exec(&mut self, data: &mut DataStore, ctx: &Context) -> Option<Signal> {
        for link in self.links {

            link.exec()
        }
    }
}

impl Mesh {
    pub fn put_chain(id: u64, 
}


mod parse {
    use serde_json::{Deserialize, Serialize};

    #{derive(Serialize, Deserialize)]
    struct LinkSpec {
        pub name: String,
        pub args: LinkArg,
    }

    #{derive(Serialize, Deserialize)]
    struct ChainSpec {
        links: Vec<LinkSpec>,
    }

    impl LinkSpec {
        pub fn create(self) -> Result<Link> {
            Link {
                spec: self,

            }
        }
    }
}
