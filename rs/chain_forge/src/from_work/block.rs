use itertools::izip;

struct Block<'a, T> {
    frames: usize,
    data: Vec<&'a mut [T]>,
}

impl<'a, T> Block<'a, T> {
    fn mono(data: &'a mut [T]) -> Self {
        let frames = data.len();
        let data = vec![data];
        Self { frames, data }
    }

    fn from_chunks(frames: usize, data: &'a mut [T]) -> Self {
        // We can't have zero channels, so need some asserts here
        let data = data.chunks_exact_mut(frames).collect();
        Self { frames, data }
    }

    fn from_channels<I, S>(slices: I) -> Self
    where
        I: Iterator<Item = S>,
        Vec<&'a mut [T]>: FromIterator<S>
    {
        let mut data: Vec<&'a mut [T]> = slices.collect();
        let mut frames: Option<usize> = None;
        for s in &mut data {
            let len = s.as_mut().len();
            assert_eq!(*frames.get_or_insert(len), len);
        }
        let frames = frames.expect("Expected at least one slice");
        Self { frames, data }
    }

    fn frames(&self) -> usize {
        self.frames
    }

    fn channels(&self) -> usize {
        self.data.len()
    }

    fn can_project_to<U>(&self, other: &Block<U>) -> bool {
        self.channels() <= other.channels()
            && (self.frames() == 1 || self.frames() == other.frames())
    }

    fn linear(&'a mut self) -> impl Iterator<Item = &'a mut T> {
        self.data.iter_mut().flat_map(|c| c.as_mut().iter_mut())
    }

    fn bi_project<U>(
        &'a mut self,
        other: &'a Block<U>,
    ) -> Option<impl Iterator<Item = (&'a mut T, &'a U)>> {
        if other.can_project_to(self) {
            Some(
                self.data
                    .iter_mut()
                    .zip(other.data.iter().cycle())
                    .flat_map(|(c1, c2)| c1.iter_mut().zip(c2.iter().cycle())),
            )
        } else {
            None
        }
    }

    fn tri_project<U, V>(
        &'a mut self,
        other: &'a Block<U>,
        another: &'a Block<V>,
    ) -> Option<impl Iterator<Item = (&'a mut T, &'a U, &'a V)>> {
        if other.can_project_to(&self) && another.can_project_to(&self) {
            Some(
                izip!(self.data.iter_mut(), other.data.iter(), another.data.iter()).flat_map(
                    |(c1, c2, c3)| {
                        izip!(
                            c1.iter_mut(),
                            c2.iter().cycle(),
                            c3.iter().cycle()
                        )
                    },
                ),
            )
        } else {
            None
        }
    }
}

fn main() {
    let mut v0: Vec<i32> = vec![0; 20];
    let mut v1: Vec<f64> = vec![1.0, 2.0, 3.0, 4.0, 5.0];
    let mut v2: Vec<f64> = vec![4.0];

    let mut s0: Block<i32> = Block::from_chunks(5, &mut v0); // Should have 4 channels
    let s1: Block<f64> = Block::mono(&mut v1);
    let s2: Block<f64> = Block::mono(&mut v2);
    
    
    s0.tri_project(&s1, &s2).unwrap().for_each(|(x, y, z)| *x = (y + z) as i32);
    // Doesn't work because the compiler thinks we're still mutably borrowing s0
    // after the previous line. Why?
    for e in s0.linear() {
        println!("{e}");
    }
}

