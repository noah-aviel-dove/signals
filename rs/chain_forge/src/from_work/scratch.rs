
struct LPF {
    order: u32,
    state: Option<Signal>,
}

impl LPF {
    fn new (order: u32) -> Self {
        let state = None;
        Self {order, state }
    }
}

impl link::func::Binary for LPF {
    fn exec(&mut self, context: &Context, sig0: &mut Signal, sig1: &Signal) {
        if let Some(state) = self.state {
            
        }
        // Need to either slice into the full buffer, or copy a slice out of it
        // Former is going to involve ugly function signatures
        // Latter is going to be inefficient
    }

    fn accepts(&self, _context: &Context, shape0: &signal::Shape, shape1: &signal::Shape) {
        shape1.can_project_framewise(shape0)
    }
}
