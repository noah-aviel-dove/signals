use std::rand::{Rng, SeedableRng, StdRng};

use crate::signal::{Signal, Scalar};

fn sin1(sig: &mut Signal) {
    sig.map_mut(Scalar::sin)
}

fn sin2(src: &Signal, dst: &mut Signal) {
    src.map_into(Scalar::sin, dst)
}

fn add2(src: &Signal, dst: &mut Signal) {
    src.map_into(Scalar::add, dst)
}

fn add3(lhs: &Signal, rhs: &Signal, dst: &mut Signal) {
    // WHEN I LEFT OFF:
    // need to consolidate last session's work before committing any of the links code
    // serisouly considering switching to just representing every signal as a 2d vector
    // trying to come up with an efficient interface for combining signals in pairs or triples
}

fn runif2(seed: &Signal, &dst: &mut Signal) {
    let seed_shape = seed.shape();
    let dst_shape = dst.shape();
    assert_eq!(seed_shape.frames, 1);
    assert_eq!(seed_shape.channels, dst_shape.channels);
    let match seed {
        //Unfortunate that matrices are stored in frame-major order
        Signal::S(s) => {
            let mut rng: StdRng = SeedableRng::from_seed(s);
            dst.map_mut(|_| rng.gen());
        },
        Signal::C(c) => {
            for s in c.data {
                let mut rng: StdRng = SeedableRng::from_seed(s);
                dst.map_mut(|_| rng.gen());
            }
        },
        Signal::M(_) => panic!("Operation not supported"),
    }
}
