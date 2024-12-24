use itertools::{cartesian_product, izip};
use std::fmt;
use std::iter::Iterator;

#[derive(PartialEq)]
struct Coord {
    pub channel: usize,
    pub frame: usize,
}

impl fmt::Display for Coord {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "({}, {})", self.channel, self.frame)
    }
}

#[derive(PartialEq)]
struct Shape {
    channels: usize,
    frames: usize,
}

impl Shape {
    fn new(channels: usize, frames: usize) -> Result<Self, String> {
        if channels == 0 {
            Err("Channels cannot be zero".into())
        } else if frames == 0 {
            Err("Frames cannot be zero".into())
        } else {
            match channels.checked_mul(frames) {
                None => Err(format!("Overflow occurred in {channels} * {frames}")),
                Some(_) => Ok(Self { channels, frames }),
            }
        }
    }

    fn channels(&self) -> usize {
        self.channels
    }

    fn frames(&self) -> usize {
        self.frames
    }

    fn size(&self) -> usize {
        self.frames * self.channels
    }

    fn is_instant(&self) -> bool {
        self.frames == 1
    }

    fn is_mono(&self) -> bool {
        self.channels == 1
    }

    fn is_scalar(&self) -> bool {
        self.is_instant() && self.is_mono()
    }

    fn can_project_channelwise(&self, target: &Self) -> bool {
        self.is_mono() && (self.is_instant() || self.frames == target.frames)
    }

    fn can_project_framewise(&self, target: &Self) -> bool {
        self.is_instant() && (self.is_mono() || self.channels == target.channels)
    }

    fn can_project(&self, target: &Self) -> bool {
        self.can_project_framewise(target) || self.can_project_channelwise(target)
    }

    fn with_channels(&self, channels: usize) -> Result<Self, String> {
        Self::new(channels, self.frames)
    }

    fn with_frames(&self, frames: usize) -> Result<Self, String> {
        Self::new(self.channels, frames)
    }
}

impl fmt::Display for Shape {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}x{}", self.channels, self.frames)
    }
}

type Pulse = f32;

struct Signal {
    data: Vec<Pulse>,
    frames: usize,
}

impl Signal {
    fn new(shape: &Shape) -> Self {
        Self::constant(shape, 0.0)
    }

    fn constant(shape: &Shape, value: Pulse) -> Self {
        Self {
            data: vec![value; shape.size()],
            frames: shape.frames,
        }
    }

    fn frames(&self) -> usize {
        self.frames
    }

    fn channels(&self) -> usize {
        let size = self.size();
        assert_eq!(0, size % self.frames);
        size / self.frames
    }

    fn size(&self) -> usize {
        self.data.len()
    }

    fn shape(&self) -> Shape {
        Shape::new(self.channels(), self.frames()).unwrap()
    }

    fn iter(&self) -> impl Iterator<Item = Pulse> {
        self.data.iter()
    }

    fn iter_mut(&mut self) -> impl Iterator<Item = &mut Pulse> {
        self.data.iter_mut()
    }
    
    /*
    fn iter_channels(&self) -> impl Iterator<Item = [Pulse]> {
        self.data.chunks_exact(self.frames())
    }

    fn iter_channels_mut(&mut self) -> impl Iterator<Item = [&mut Pulse]> {
        self.data.chunks_exact_mut(self.frames())
    }

    fn iter_frames(&self, start: usize, stop: usize) -> impl Iterator<Item = Iterator> {
        let frames = self.frames();
        (start..stop)
            .iter()
            .map(|offset| self.data.iter().skip(offset).step_by(frames))
    }

    fn iter_frames_mut(&mut self) -> impl Iterator<Item = Iterator> {
        let frames = self.frames();
        (0..frames)
            .iter()
            .map(|offset| self.data.iter_mut().skip(offset).step_by(frames))
    }
    */

    fn get_channel(&self, index: usize) -> [Pulse] {
        let frames = self.frames();
        let start = index * frames;
        self.data[start..start + frames]
    }

    fn get_frame(&self, index: usize) -> impl Iterator<Item = Pulse> {
        self.data.iter().skip(index).step_by(self.frames())
    }

    fn mut_with(&mut self, mut func: impl FnMut(&mut Pulse, Pulse), sig1: &Signal) {
        let this_shape = self.shape();
        let that_shape = sig1.shape();
        if this_shape == that_shape {
            self.data
                .iter_mut()
                .zip(sig1.data.iter())
                .for_each(|(x, y)| func(x, *y))
        } else if that_shape.can_project_channelwise(&this_shape) {
            self.data
                .iter_mut()
                .zip(sig1.data.iter().cycle())
                .for_each(|(x, y)| func(x, *y))
        } else if that_shape.can_project_framewise(&this_shape) {
            self.mut_frames(|frame| {
                frame
                    // Don't need to cycle because previous branch handled the scalar case
                    .zip(sig1.data.iter())
                    .for_each(|(x, y)| func(x, *y))
            })
        } else {
            panic!("Can't project {that_shape} to {this_shape}")
        }
    }

    fn mut_with_2(
        &mut self,
        func: impl FnMut(&mut Pulse, Pulse, Pulse),
        sig1: &Signal,
        sig2: &Signal,
    ) {
        let this_shape = self.shape();
        let that_shape = sig1.shape();
        let that_other_shape = sig2.shape();
        if this_shape == that_shape && this_shape == that_other_shape {
            izip!(self.data.iter_mut(), sig1.data.iter(), sig2.data.iter()).for_each(func)
        } else if this_shape == that_shape && that_other_shape.can_project_channelwise(&this_shape)
        {
            izip!(
                self.data.iter_mut(),
                sig1.data.iter(),
                sig2.data.iter().cycle()
            )
            .for_each(func)
        } else if this_shape == that_other_shape && that_shape.can_project_channelwise(&this_shape)
        {
            izip!(
                self.data.iter_mut(),
                sig1.data.iter().cycle(),
                sig2.data.iter()
            )
            .for_each(func)
        } else if that_shape.can_project_channelwise(&this_shape)
            && that_other_shape.can_project_channelwise(&this_shape)
        {
            izip!(
                self.data.iter_mut(),
                sig1.data.iter().cycle(),
                sig2.data.iter().cycle()
            )
            .for_each(func)
        // sig1 and sig2 cannot both be scalar below this point
        } else if this_shape == that_shape && that_other_shape.can_project_framewise(&this_shape) {
            self.mut_frames(|frame| {
                izip!(frame, sig1.data.iter(), sig2.data.iter().cycle()).for_each(func)
            })
        // Neither sig1 nor sig2 can be scalar below this point
        } else if this_shape == that_other_shape && that_shape.can_project_framewise(&this_shape) {
            self.mut_frames(|frame| {
                izip!(frame, sig1.data.iter().cycle(), sig2.data.iter()).for_each(func)
            })
        } else if that_shape.can_project_framewise(&this_shape)
            && that_other_shape.can_project_framewise(&this_shape)
        {
            self.mut_frames(|frame| {
                izip!(frame, sig1.data.iter().cycle(), sig2.data.iter().cycle()).for_each(func)
            })
        } else if (that_shape.can_project_channelwise(&this_shape)
            && that_other_shape.can_project_framewise(&this_shape))
            || (that_shape.can_project_framewise(&this_shape)
                && that_other_shape.can_project_channelwise(&this_shape))
        {
            self.data
                .iter_mut()
                .zip(sig1.data.iter().cartesian_product(sig2.data.iter()))
                .for_each(|(x, (y, z))| func(x, y, z))
        } else {
            panic!("Can't project {that_shape} and {that_other_shape} to {this_shape}")
        }
    }
}
