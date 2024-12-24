use link::arg;
use link::func;
use link::func::Context;
use link::ops;
use signal;
use signal::{Pulse, Signal};

static sine: ops::ParallelUnary = ops::ParallelUnary { func: Pulse::sin };
static add: ops::ParallelBinary = ops::ParallelBinary { func: Pulse::add };
static mul: ops::ParallelBinary = ops::ParallelBinary { func: Pulse::mul };

struct Clock;

impl func::Unary for Clock {
    fn exec(&self, &context: Context, &mut sig0: Signal) {
        let mut clock = context.track_frame..(context.track_frame + context.block_size);
        sig0.mut_linear(|x| *x = clock.next().unwrap().into())
    }

    fn accepts(&self, &context: Context, &shape0: signal::Shape) -> bool {
        shape0.is_mono() && shape.frames() == context.block_size
    }

    fn mode(&self) -> arg::Mode {
        arg::Mode::WriteOnly
    }

    fn outline(&self, &context: Context) -> Option<signal::Shape> {
        Some(signal::Shape::new(1, context.block_size))
    }
}

trait Noise: BinaryLink {
    type Rng;
}

impl func::Binary for Noise {
    fn exec(&mut self, &_context: Context, &mut sig0: Signal, &sig1: Signal) {
        let rngs = sig1
            .iter()
            .map(|x| R::seed_from_u64(x.into() + context.frame))
            .cycle();
        sig0.mut_channels(|c| c.try_fill(rngs.next().unwrap()).unwrap())
    }

    fn accepts(&self, &shape0: &signal::Shape, &shape1: signal::Shape) -> bool {
        shape1.can_project_framewise(shape0)
    }

    fn modes(&self) -> [arg::Mode; 2] {
        [arg::Mode::WriteOnly, arg::Mode::ReadOnly]
    }

    fn outline(
        &self,
        context: &Context,
        shape0: &Option<signal::Shape>,
        shape1: &Option<signal::Shape>,
    ) -> Option<[signal::Shape; 2]> {
        match (shape0, shape1) {
            // Is this overzealous inference? Would it be better to just return None?
            (None, None) => Some([Shape::new(1, 1), Shape::new(1, context.frames)]),
            (Some(shape0), None) => Some([shape0.clone(), shape0.with_frames(context.frames)]),
            (None, Some(shape1)) => Some([shape1.with_frames(1), shape1.clone()]),
            (Some(shape0), Some(shape1)) => Some([shape0.clone(), shape1.clone()]),
        }
    }
}
