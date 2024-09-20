mod prelude {
    use rand::Rng;

    const CHUNK_SIZE: usize = 1_000;

    pub fn setup() -> [Vec<f64>; 2] {
        let mut x = Vec::with_capacity(CHUNK_SIZE);
        let mut y = Vec::with_capacity(CHUNK_SIZE);
        for _ in 1..CHUNK_SIZE {
            x.push(rand::thread_rng().gen());
            y.push(rand::thread_rng().gen());
        }

        [x, y]
    }

    pub trait ParallelBinOp {
        fn produce_method(&self, x: f64, y: f64) -> f64;

        fn produce(x: f64, y: f64) -> f64;

        fn mutate(x: &mut f64, y: f64);
    }

    pub struct Add;

    impl ParallelBinOp for Add {
        fn produce_method(&self, x: f64, y: f64) -> f64 {
            x + y
        }

        fn produce(x: f64, y: f64) -> f64 {
            x + y
        }

        fn mutate(x: &mut f64, y: f64) {
            *x += y
        }
    }

    pub struct Sub;

    impl ParallelBinOp for Sub {
        fn produce_method(&self, x: f64, y: f64) -> f64 {
            x - y
        }

        fn produce(x: f64, y: f64) -> f64 {
            x - y
        }

        fn mutate(x: &mut f64, y: f64) {
            *x -= y
        }
    }
}

mod inline {

    pub fn vec_add(x: &[f64], y: &[f64]) -> Vec<f64> {
        let mut result = Vec::with_capacity(x.len());
        for (xn, yn) in x.iter().zip(y.iter()) {
            result.push(xn + yn);
        }

        result
    }

    pub fn vec_sub(x: &[f64], y: &[f64]) -> Vec<f64> {
        let mut result = Vec::with_capacity(x.len());
        for (xn, yn) in x.iter().zip(y.iter()) {
            result.push(xn - yn);
        }

        result
    }
}

mod generic {
    use crate::prelude::*;

    fn vec_op<Op: ParallelBinOp>(x: &[f64], y: &[f64]) -> Vec<f64> {
        let mut result = Vec::with_capacity(x.len());
        for (xn, yn) in x.iter().zip(y.iter()) {
            result.push(Op::produce(*xn, *yn));
        }

        result
    }

    pub fn vec_add(x: &[f64], y: &[f64]) -> Vec<f64> {
        vec_op::<Add>(x, y)
    }

    pub fn vec_sub(x: &[f64], y: &[f64]) -> Vec<f64> {
        vec_op::<Sub>(x, y)
    }
}

mod polymorphic {
    use crate::prelude::*;

    fn vec_op(op: &impl ParallelBinOp, x: &[f64], y: &[f64]) -> Vec<f64> {
        let mut result = Vec::with_capacity(x.len());
        for (xn, yn) in x.iter().zip(y.iter()) {
            result.push(op.produce_method(*xn, *yn));
        }

        result
    }

    pub fn vec_add(x: &[f64], y: &[f64]) -> Vec<f64> {
        vec_op(&Add, x, y)
    }

    pub fn vec_sub(x: &[f64], y: &[f64]) -> Vec<f64> {
        vec_op(&Sub, x, y)
    }
}

fn main() {
    use rand::seq::SliceRandom;
    use std::collections::HashMap;
    use std::io;
    use std::time::Instant;

    type VecOp = fn(&[f64], &[f64]) -> Vec<f64>;

    let [x, y] = prelude::setup();

    let mut total = 0.0;

    let mut times: HashMap<&str, u128> = HashMap::new();

    let adders = HashMap::from([
        ("generic", generic::vec_add as VecOp),
        ("polymorphic", polymorphic::vec_add as VecOp),
        ("inline", inline::vec_add as VecOp),
    ]);

    let subbers = HashMap::from([
        ("generic", generic::vec_sub as VecOp),
        ("polymorphic", polymorphic::vec_sub as VecOp),
        ("inline", inline::vec_sub as VecOp),
    ]);

    let mut choice = String::new();

    println!("Which op?");
    io::stdin().read_line(&mut choice).expect("IO Error");

    let funcs = match choice.as_str().trim() {
        "add" => adders,
        "sub" => subbers,
        _ => panic!("wrong choice"),
    };

    println!("Ok, doing test");

    for _ in 1..1_000_000 as i64 {
        let mut names = funcs.keys().collect::<Vec<&&str>>();

        names.shuffle(&mut rand::thread_rng());

        for name in names {
            let func = funcs[name];
            let start = Instant::now();
            total += func(&x, &y).last().expect("Empty vec");
            *times.entry(name).or_insert(0) += start.elapsed().as_nanos();
        }
    }

    println!("{}", total);
    println!("{:?}", times);
}
