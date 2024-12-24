use link::def::Def;
use link::arg;

struct Library {
    links_by_name: HashMap<String, Def>,
}

impl Library {
    fn new() -> Self {
        Self {
            links_by_name: HashMap::<_, _>::new(),
        }
    }

    fn register(&mut self, def: Def) {
        self.links_by_name.insert(def.name.clone(), def);
    }

    fn lookup<'a>(&'a self, name: &str) -> Option<&'a Def> {
        self.links_by_name.get(name)
    }
}

fn load(lib: &mut Library) {
    let defs = [
        Def::unary("sin1", &implementations::sine),
        Def::binary("sin2", &implementation::sine),

        Def::binary("add2", &implementations::add),
        Def::trinary("add3", &implementations::add),

        Def::binary("mul2", &implementations::mul),
        Def::trinary("mul3", &implementations::mul),

        Def::unary("clock", &implementations::clock),

        Def::binary("wnoiz", &implementation::noise),
    ];

    defs.into_iter().for_each(|def| lib.register(def));
}
