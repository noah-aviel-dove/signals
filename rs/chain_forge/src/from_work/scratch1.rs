struct Window<'a> {
    pub slice: &'a mut [i32],
}

impl<'a> Window<'a> {

    fn f1(&mut self) -> impl Iterator<Item = &mut i32> {
        self.slice.iter_mut()
    }
    
    fn f2(&mut self) -> impl Iterator<Item = &mut i32> {
        self.slice.chunks_exact_mut(2).flat_map(|s| s.iter_mut())
    }
}

fn main() {
    let mut v: Vec<i32> = vec![0; 5];
    let mut w: Window = Window { slice: &mut v };

    for iter_1 in w.f1() {
        println!("{iter_1}");
    }
    // Doesn't work because the compiler thinks we're still mutably borrowing s0
    // after the previous loop. Why?
    for iter_2 in w.f2() {
        println!("{iter_2}");
    }
}

