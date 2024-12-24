use link::func::Context;
use link::link::Link;
use signal;
use signal::Signal;

struct Chain {
    // Defined in spec
    // Does not change during execution
    // Reforge when a value needs to be updated
    vars: Vec<Signal>,
    // Starts empty
    // Each element should be updated once per execution,
    // and read/replaced on the next execution.
    // Not implmenting this yet (?), but it's needed for (e.g.) filters
    state: Vec<Signal>,
    // Starts empty
    // Each element may be overwritten multiple times per execution,
    // and should not be accessed once the current execution is complete.
    stack: Vec<Signal>,

    links: Vec<Link>,
}

impl Chain {
    
    fn output(&mut self, context: &Context) {
        self.read_buffer().unwrap_or_else(|| {
            let block = self.exec(context);
            self.write_buffer(context, block);
            block
        })
    }

    fn exec(&mut self, context: &Context) {
        for link in &self.links {
            link.exec(context, self);
        }
    }

    fn write_buffer(&self, context: &Context, sig: &Signal) {

    }

    fn read_buffer(&self, context: &Context, sig: &Signal) -> Option<Signal> {

    }
    
    fn clear_buffer(&self) {

    }

    fn reset(&mut self) {
        self.clear_buffer();
        // Should be safe to leave the stack alone.
        // Forge step should prove that we only read from fresh locations.
        for sig in self.state.iter_mut() {
            sig.mut_linear(|x| *x = 0);
        }
    }
}

impl link::SignalSource for Chain {
    fn load<'a>(&'a mut self, arg_spec: &arg::Spec) -> &'a mut Signal {
        // I think because we borrow self as mutable,
        // the borrow checker will be satisfied that the lifetime is valid
        // because there can't exist another mutable reference to self
        // that could cause the returned reference to become invalid
        // e.g. by shrinking the stack
        // ... but that doesn't work, because we NEED another mutable reference to self
        // when we load multiple arguments. Shit.
        // ... This reflects the underlying fact that shit might break if we load the same
        // signal twice, i.e., break the aliasing rules by creating two references
        // to the same signal.
        // I think there's no way around having at least one of the arguments, 
        // and maybe all of them supplied via unsafe raw ptr.
        let data = match arg.src {
            link::arg::Location::Var => self.vars,
            link::arg::Location::State => self.state,
            link::arg::Location::Stack => self.stack,
        };
        &mut data[arg.index]
    }
}

