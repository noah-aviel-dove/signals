type Pulse = i32;

struct Signal {
    pub frames: usize,
    pub channels: usize,
    pub data: Vec<Pulse>,
}

trait SignalAccess<'a> {
    type SLICE;
    type LIN: Iterator;
    type MAJ: Iterator;

    fn linear(sig: Self::SLICE) -> Self::LIN;

    fn major(sig: Self::SLICE, size: usize) -> Self::MAJ;
    
    fn minor(sig: Self::SLICE, size: usize) -> impl Iterator<Item = std::iter::StepBy<std::iter::Skip<Self::LIN>>>;
}

struct Const;

impl <'a> SignalAccess<'a> for Const {
    type SLICE = &'a [Pulse];
    type LIN = std::slice::Iter<'a, Pulse>;
    type MAJ = std::slice::ChunksExact<'a, Pulse>;

    fn linear(sig: Self::SLICE) -> Self::LIN {
        sig.iter()
    }
    
    fn major(sig: Self::SLICE, size: usize) -> Self::MAJ {
        sig.chunks_exact(size)
    }
    
    fn minor(sig: Self::SLICE, size: usize) -> impl Iterator<Item = std::iter::StepBy<std::iter::Skip<Self::LIN>>> {
        (0..size).map(move |offset| sig.iter().skip(offset).step_by(size))
    }
}

struct Mut;

impl <'a> SignalAccess<'a> for Mut {
    type SLICE = &'a mut [Pulse];
    type LIN = std::slice::IterMut<'a, Pulse>;
    type MAJ = std::slice::ChunksExactMut<'a, Pulse>;
    
    fn linear(sig: Self::SLICE) -> Self::LIN {
        sig.iter_mut()
    }
    
    fn major(sig: Self::SLICE, size: usize) -> Self::MAJ {
        sig.chunks_exact_mut(size)
    }
    
    fn minor(sig: Self::SLICE, size: usize) -> impl Iterator<Item = std::iter::StepBy<std::iter::Skip<Self::LIN>>> {
        let p = sig as *mut [Pulse];
        (0..size).map(move |offset| unsafe {(*p).iter_mut().skip(offset).step_by(size)})
    }
}


fn main() {
    let s = Signal {
        frames: 5,
        channels: 2,
        data: [0; 10]
    };
    
    println!("{}", "Linear:");
    // Stopped in the middle of re-writing main when I realized that the `mut`
    // on this line is a dealbreaker. Saving work here to begin a new approach.
    for (i, e) in Mut::linear(&mut s.data).enumerate() {
        *e = i;
    }
    
    for (i, e) in Const::linear(&s.data).enumerate() {
        println!("{i}: {e}");
    }
    
    println!("{}", "\nMajor order:");
    for (i, c) in Const::major(&s.data, s.frames).enumerate() {
        
    }
    
    println!("{}", "\nMinor order:");
    for (i, f) in Const::minor(&s.data, s.frames).enumerate() {
        let f: Vec<_> = f.collect();
        println!("{i}: {f:?}");
    }    
}

