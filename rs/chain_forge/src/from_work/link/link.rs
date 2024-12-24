use std::collections::HashMap;

use signal::Signal;

use link::arg;
use link::arg::Arg;
use link::func::Func;
use link::library::Library;

struct Spec {
    pub name: String,
    pub args: Vec<arg::Spec>,
}

struct Link {
    func: Func,
    args: Vec<Arg>,
    buffer: Option<Buffer>,
}

impl Link {
    fn args<'a>(&self) -> &'a [Arg] {
        &self.args
    }

    fn is_buffered(&self) -> bool {
        self.buffer.is_some()
    }

    fn create(lib: &Library, spec: &Spec) -> Result<Self, String> {
        let name = spec.name;
        let def = lib
            .lookup(&name)
            .ok_or_else(|| format!("No definition found for link {:?}", spec.name))?;
        let modes = def.modes();
        let defined_arity = modes.len();
        let provided_arity = spec.args.len();
        if defined_arity != provided_arity {
            Err(format!(
                "Link '{name}' expected {defined_arity} arguments but received {provided_arity}",
            ))
        } else {
            let func = def.func.clone();
            let args = spec
                .args
                .iter()
                .zip(modes.iter())
                .map(|(spec, mode)| Arg::new(spec.clone(), *mode))
                .collect::<Result<Vec<Arg>, String>>()?;
            if args.iter().duplicates().next().is_some() {
                // This is where we manually enforce the aliasing rules: no two arguments 
                // can simultaneously borrow the same data from the chain.
                Err(format!("Arg specs must be unique: {args:?}"))
            } else {
                Ok(Self { func, args })
            }
        }
    }

    fn exec<'a>(&self, context: &Context, source: &'a mut impl SignalSource) {
        // Broken here because we can't create take multiple mutable
        // borrowings from the source
        let args = self.args.iter().map(|arg| source.load(&arg.spec));
        self.func.exec(context, args);
    }

    fn max_arg_index(&self, loc: arg::Location) -> Option<usize> {
        self.args
            .iter()
            .filter_map(|arg| if arg.spec.loc == loc { Some(arg.spec.index) } else { None})
            .max()
    }
}
