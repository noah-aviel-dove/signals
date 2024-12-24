

fn Chain::exec(&mut self, frame: usize) {
    
    for link in &self.links {
        let mut frames = 0;
        while frames < self.block_size {
            frames += link.exec(&mut self, 
                                frame + frames, 
                                self.block_size - frames);
        }
        if frames > self.block_size {
            // technically, nothing needs to be done here.
            // but we ought to save the trailing frames.
            // can this be dealt with within the link?
        }
    }
}



fn Link::exec(&self, chain: &mut Chain, frame: usize, size_hint: usize) {
    
}
