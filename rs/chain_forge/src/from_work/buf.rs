
struct Block <P> {
    channels: usize,
    frames: usize,
    data: Vec<P>,
}

struct Buf {
    data: Vec<Vec<P>>
    
}

struct Window <'a, P> {
    pub channels: Vec<&'a mut [P]>
}


impl Block<P> {
    
    fn frames(&self) -> usize {
        self.frames
    }
    
    fn channels(&self) -> usize {
        self.channels
    }

    fn view(&'a mut self) -> Window<'a, P> {
        Window {
            channels: self.data.chunks_mut_exact().collect()
        }
    }
}
