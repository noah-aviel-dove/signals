//No dependencies, yay!

#[derive(Copy, Clone, Debug, PartialEq)]
enum Location {
    Var,
    State,
    Stack,
}

#[derive(Copy, Clone, Debug, PartialEq)]
struct Spec {
    pub loc: Location,
    pub index: usize,
}

#[derive(Copy, Clone, Debug, PartialEq)]
enum Mode {
    ReadOnly,
    WriteOnly,
    ReadAndWrite,
}

impl Mode {
    fn is_read(&self) -> bool {
        match self {
            Self::ReadOnly => true,
            Self::WriteOnly => false,
            Self::ReadAndWrite => true,
        }
    }

    fn is_written(&self) -> bool {
        match self {
            Self::ReadOnly => false,
            Self::WriteOnly => true,
            Self::ReadAndWrite => true,
        }
    }
}

#[derive(Debug, PartialEq)]
struct Arg {
    pub spec: Spec,
    pub mode: Mode,
}

impl Arg {
    fn new(spec: Spec, mode: Mode) -> Result<Self, String> {
        let loc = spec.loc;
        // Technically I'm not sure if this would break anything, but it
        // almost certainly indicates a semantic error
        if (loc == Location::Var && mode != Mode::ReadOnly)
            || (loc == Location::State && mode != Mode::ReadAndWrite)
        {
            Err(format!("Mode {mode:?} not allowed for location {loc:?}"))
        } else {
            Ok(Self { spec, mode })
        }
    }

    fn spec<'a>(&'a self) -> &'a Spec {
        &self.spec
    }

    fn mode<'a>(&'a self) -> &'a Mode {
        &self.mode
    }
}
