
struct SignalStorageBuilder {
    loc: link::arg::Location,
    shapes: Vec<Option<signal::Shape>>,
}

impl SignalStorageBuilder {
    fn new(loc: signal::arg::Location, links: &[Link]) -> Self {
        let size = links
            .filter_map(|link| link.max_arg_index(loc))
            .max()
            .unwrap_or(0);
        let shapes = Vec::<Option<signal::Shape>>::with_capacity(size);
        Self { loc, shapes }
    }

    fn get_shape<'a>(&self, index: usize) -> &'a Option<signal::Shape> {
        self.shapes.get(index)
    }

    fn put_shape(&mut self, index: usize, shape: signal::Shape) -> Result<(), String> {
        let loc = self.loc;
        match self.shapes.get(index) {
            None => Err(format!("Index {index} OOB in {loc}")),
            Some(None) => {
                self.shapes[index] = Some(shape);
                Ok(())
            }
            Some(Some(_)) => Err(format!(
                "Conficting shapes at index {index} in {loc}: {shape}, {other_shape}"
            )),
        }
    }

    fn build(&self) -> Result<Vec<Signal>, String> {
        let loc = self.loc;
        self.shapes
            .iter()
            .enumerate()
            .map(|(i, opt_shape)| {
                opt_shape
                    .ok_or_else(|| format!("Failed to infer signal shape at index {i} in {loc}"))
                    .map(|shape| Signal::new(shape))
            })
            .collect()
    }
}

struct ChainBuilder {
    pub state: SignalStorageBuilder,
    pub stack: SignalStorageBuilder,
}

impl ChainBuilder {
    fn new(links: &[Link]) -> Self {
        let state = SignalStorageBuilder::new(link::arg::Location::State, links);
        let stack = SignalStorageBuilder::new(link::arg::Location::Stack, links);
        Self { state, stack }
    }

    fn get_shape(&self, vars: &[Signal], arg: &link::Arg) -> Result<Option<signal::Shape>, String> {
        let spec = arg.spec();
        let loc = spec.loc;
        let index = spec.index;
        let shape = match loc {
            link::arg::Location::Var => vars.get(index).map(|sig| &sig.shape()),
            link::arg::Location::State => self.state.get_shape(index),
            link::arg::Location::Stack => self.stack.get_shape(index),
        };
        shape.ok_or_else(|| format!("Arg index OOB in {loc} at {index}"))
    }

    fn put_shape(
        &mut self,
        vars: &[Signal],
        arg: &link::Arg,
        shape: signal::Shape,
    ) -> Result<(), String> {
        let spec = arg.spec();
        let loc = spec.loc;
        let index = spec.index;
        let shape = match loc {
            link::arg::Location::Var => vars.get(index).map(|sig| &sig.shape()),
            link::arg::Location::State => self.state.get_shape(index),
            link::arg::Location::Stack => self.stack.get_shape(index),
        };
        shape.ok_or_else(|| format!("Arg index OOB in {loc} at {index}"))
    }

    fn infer_shapes(&self, context: &Context, link: &Link) -> Result<(), String> {
        let known_shapes: Vec<Option<signal::Shape>> = link
            .args()
            .iter()
            .map(|arg| self.get_shape(arg))
            .collect::<Result<_, _>>()?;

        let inferred_shapes: Vec<signal::Shape> = link
            .func()
            .outline(&context, &known_shapes)
            .ok_or_else(|| format!("Link {link} failed to infer signal shapes"))?;

        for (arg, known_shape, inferred_shape) in
            izip!(args.iter(), known_shapes.iter(), inferred_shapes.iter())
        {
            if let Some(shape) = known_shape {
                assert_eq!(shape, inferred_shape);
            } else {
                match arg.spec().loc {
                    link::arg::Location::Var => panic!("Var shape must be known"),
                    link::arg::Location::State => self.state.put_shape(index, shape),
                    link::arg::Location::Stack => self.stack.put_shape(index, shape),
                }
            }
        }
    }
}

struct Spec {
    pub vars: Vec<Signal>,
    // Optimization: use arbitrary integers (or even strings) for link arg indices,
    // then translate to stack indices at this step
    pub links: Vec<link::Spec>,
}

impl Spec {
    fn forge(self, link_lib: &link::Library) -> Result<Chain, String> {
        let vars = self.vars;
        let links = self
            .links
            .into_iter()
            .map(|link_spec| Link::create(link_lib, link_spec))
            .collect::<Result<Vec<Link>, String>>()?;
        
        // this was based on the idea that writing to a buffer would always (and only)
        // happen at the end of a chain. probably not going to keep it.
        let (stack_end,) = links.
            last()
            .ok_or("Chain has no links".into())?
            .args
            .iter()
            .filter_map(|a| {
                if arg.mode.is_written() && arg.spec.loc == link::arg::Location::Stack {
                    Some(arg.spec.index)
                } else {
                    None
                }))
            .collect_tuple()
            .ok_or("Last link has no unambiguous reciever".into());

        let builder = ChainBuilder::new(&links);
        let context = Context::placeholder();
        for link in &links {
            builder.infer_shapes(&context, &vars, &link)?;
        }
        let state = builder.state.build()?;
        let stack = builder.stack.build()?;

        Ok(Chain {
            vars,
            state,
            stack,
            links,
        })
    }
}
