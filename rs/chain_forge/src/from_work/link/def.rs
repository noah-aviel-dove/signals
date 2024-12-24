use link::arg;
use link::func;
use link::func::Func;

struct Def {
    pub name: String,
    pub func: Func,
}

impl LinkDef {
    fn unary(name: &str, func: &'static impl func::Unary) -> Self {
        Self {
            name: name.to_owned(),
            func: Func::Unary(func),
        }
    }

    fn binary(
        name: &str,
        func: &'static impl func::Binary
    ) -> Self {
        Self {
            name: name.to_owned(),
            func: Func::Binary(func),
        }
    }

    fn trinary(
        name: &str,
        func: &'static impl func::Trinary
    ) -> Self {
        Self {
            name: name.to_owned(),
            func: Func::Trinary(func),
        }
    }
}
