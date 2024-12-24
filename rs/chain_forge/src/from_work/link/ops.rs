use link::func;
use link::func::Context;
use signal;
use signal::{Pulse, Signal};

struct ParallelUnary {
    func: &'static fn(Pulse) -> Pulse,
}

struct ParallelBinary {
    func: &'static fn(Pulse, Pulse) -> Pulse,
}

impl func::Unary for ParallelUnary {
    fn exec(&self, &_context: Context, &mut sig0: Signal) {
        sig0.mut_linear(|x| *x = self.func(x))
    }

    fn accepts(&self, &_shape0: signal::Shape) -> bool {
        true
    }

    fn mode(&self) -> arg::Mode {
        arg::Mode::ReadAndWrite
    }

    fn outline(&self, &_context: Context) -> Option<signal::Shape> {
        None
    }
}

impl func::Binary for ParallelUnary {
    fn exec(&self, &_context: Context, &mut sig0: Signal, &sig1: Signal) {
        sig0.mut_with(|(x, y)| *x = self.func(y), sig1)
    }

    fn accepts(&self, &shape0: &signal::Shape, &shape1: signal::Shape) -> bool {
        shape0 == shape1 || shape1.can_project(shape0)
    }

    fn modes(&self) -> [arg::Mode; 2] {
        [arg::Mode::WriteOnly, arg::Mode::ReadOnly]
    }

    fn outline(
        &self,
        _context: &Context,
        shape0: &Option<signal::Shape>,
        shape1: &Option<signal::Shape>,
    ) -> Option<[signal::Shape; 2]> {
        match (shape0, shape1) {
            (None, None) => None,
            (Some(shape0), None) => Some([shape0.clone(); 2]),
            (None, Some(shape1)) => Some([shape1.clone(); 2]),
            (Some(shape0), Some(shape1)) => {
                if self.accepts(shape0, shape1) {
                    Some([shape0.clone(), shape1.clone()])
                } else {
                    None
                }
            }
        }
    }
}

impl func::Binary for ParallelBinary {
    fn exec(&self, &_context: Context, &mut sig0: Signal, &sig1: Signal) {
        sig0.mut_with(|(x, y)| *x = self.func(x, y), sig1)
    }

    fn accepts(&self, &shape0: &signal::Shape, &shape1: signal::Shape) -> bool {
        shape0 == shape1 || shape1.can_project(shape0)
    }

    fn modes(&self) -> [arg::Mode; 3] {
        [arg::Mode::ReadAndWrite, arg::Mode::ReadOnly]
    }

    fn outline(
        &self,
        _context: &Context,
        shape0: &Option<signal::Shape>,
        shape1: &Option<signal::Shape>,
    ) -> Option<[signal::Shape; 2]> {
        // I think this just duplicates the impl for PU
    }
}

impl func::Trinary for ParallelBinary {
    fn exec(&self, &_context: Context, &mut sig0: Signal, &sig1: Signal, &sig1: Signal) {
        sig0.mut_with_2(|(x, y, z)| *x = self.func(y, z), sig1, sig2)
    }

    fn accepts(&self, &shape0: &signal::Shape, &shape1: signal::Shape, &shape2: signal::Shape) -> bool {
        // Haven't 100% thought this through
        (shape0 == shape1 && shape0 == shape2) ||
        (shape0 == shape1 && shape2.can_project(shape0)) ||
        (shape0 == shape2 && shape1.can_project(shape0)) ||
        (shape1 == shape2 && shape1.can_project(shape0)) ||
        // This one is especially questionable
        (shape1.can_project(shape0) && shape2.can_project(shape0))
    }

    fn modes(&self) -> [arg::Mode; 3] {
        [
            arg::Mode::WriteOnly,
            arg::Mode::ReadOnly,
            arg::Mode::ReadOnly,
        ]
    }

    fn outline(
        &self,
        context: &Context,
        shape0: &Option<signal::Shape>,
        shape1: &Option<signal::Shape>,
        shape1: &Option<signal::Shape>,
    ) -> Option<[signal::Shape; 3]> {
        // old shit, not appliccable
        if shape1 == shape2 || shape2.can_project(shape1) {
            shape1.clone()
        } else if shape1.can_project(shape2) {
            shape2.clone()
        }
    }
}
