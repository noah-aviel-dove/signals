
impl Conv {
    
    fn accepts(
        &self, 
        _context: &Context, 
        y_shape: &Shape, 
        x_shape: &Shape, 
        h_shape: &Shape, 
        pad_shape: &Shape
    ) {
        x_shape == y_shape 
            && h_shape.channels() == pad_shape.channels() 
            && h_shape.frames() == pad_shape.frames() + 1 
            && h_shape.can_project_channelwise(x_shape) 
            && (x_shape.frames() + pad_frames.frames()).is_power_of_two()
    }

    // Assuming the filter has already been dft'd
    fn exec(&self, _context: &Context, y: &mut Signal, x: &Signal, H: &Signal, p: &Signal) {
        let x = concat_frames(p, x);
        // blueagh
        let yt = idft(dft(x) * H)
         
    }

}
