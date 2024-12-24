use itertools::Itertools;

use signal;
use signal::Signal;

use link::arg;
use link::arg::Arg;

struct Context {
    pub track_frame: usize,
    pub event_frame: Option<usize>,
    pub block_size: usize,
}

trait Unary {
    fn exec(&self, context: &Context, sig0: &mut Signal);

    fn accepts(&self, shape0: &signal::Shape) -> bool;

    fn mode(&self) -> arg::Mode;

    fn outline(&self, context: &Context) -> Option<signal::Shape>;
}

trait Binary {
    fn exec(&self, context: &Context, sig0: &mut Signal, sig1: &Signal);

    fn accepts(&self, shape0: &signal::Shape, shape1: &signal::Shape) -> bool;

    fn modes(&self) -> [arg::Mode; 2];

    fn outline(
        &self,
        context: &Context,
        shape0: &Option<signal::Shape>,
        shape1: &Option<signal::Shape>,
    ) -> Option<[signal::Shape; 2]>;
}

trait Trinary {
    fn exec(&self, context: &Context, sig0: &mut Signal, sig1: &Signal, sig2: &Signal);

    fn accepts(
        &self,
        shape0: &signal::Shape,
        shape1: &signal::Shape,
        shape2: &signal::Shape,
    ) -> bool;

    fn modes(&self) -> [arg::Mode; 3];

    fn outline(
        &self,
        context: &Context,
        shape0: &Option<signal::Shape>,
        shape1: &Option<signal::Shape>,
        shape1: &Option<signal::Shape>,
    ) -> Option<[signal::Shape; 3]>;
}

trait SignalSource<'a> {
    fn load(&self, arg: &Arg) -> &'a Signal;

    fn load_mut(&mut self, arg: &Arg) -> &'a mut Signal;
}

#[derive(Clone)]
enum Func {
    Unary(&'static dyn Unary),
    Binary(&'static dyn Binary),
    Trinary(&'static dyn Trinary),
}

impl Func {
    fn exec<'a>(&self, context: &Context, source: &mut impl SignalSource, args: &[Arg]) {
        match self {
            Self::Unary(uf) => {
                assert_eq!(1, args.len());
                let a0 = source.load_mut(args[0]);
                assert!(uf.accepts(&a0.shape()));
                uf.exec(context, a0);
            }
            Self::Binary(bf) => {
                assert_eq!(2, args.len());
                let a0 = source.load_mut(args[0]);
                let a1 = source.load(args[1]);
                assert!(bf.accepts(&a0.shape(), &a1.shape()));
                bf.exec(context, a0, a1);
            }
            Self::Trinary(tf) => {
                // this still won't work, but i think it's closer
                let a0 = source.load_mut(args[0]);
                let a1 = source.load(args[1]);
                let a2 = source.load(args[2]);
                assert!(tf.accepts(&a0.shape(), &a1.shape(), &a2.shape()));
                tf.exec(context, a0, a1, a2);
            }
        }
    }

    fn modes(&self) -> Vec<arg::Mode> {
        match self {
            Self::Unary(uf) => vec![uf.mode()],
            Self::Binary(bf) => bf.modes().into(),
            Self::Trinary(tf) => tf.modes().into(),
        }
    }

    fn outline(
        &self,
        context: &Context,
        shapes: &[Option<signal::Shape>],
    ) -> Option<Vec<signal::Shape>> {
        match self {
            Self::Unary(uf) => {
                assert_eq!(1, shapes.len());
                shapes[0]
                    .or_else(|| uf.outline(context))
                    .map(|shape0| vec![shape0])
            }
            Self::Binary(bf) => {
                assert_eq!(2, shapes.len());
                bf.outline(&shapes[0], &shapes[1])
                    .map(|shapes| shapes.into())
            }
            Self::Trinary(tf) => {
                assert_eq!(3, shapes.len());
                bf.outline(&shapes[0], &shapes[1], &shapes[2])
                    .map(|shapes| shapes.into())
            }
        }
    }
}
