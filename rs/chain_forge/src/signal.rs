use std::fmt;

use serde::{Deserialize, Serialize};

pub type Scalar = f32;

#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
pub struct Column {
    pub data: Vec<Scalar>,
}

#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
pub struct Matrix {
    pub data: Vec<Scalar>,
    pub channels: usize,
}

const SIGNAL_S: u8 = b's';
const SIGNAL_C: u8 = b'c';
const SIGNAL_M: u8 = b'm';

#[repr(u8)]
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum SignalKind {
    S = SIGNAL_S,
    C = SIGNAL_C,
    M = SIGNAL_M,
}

#[repr(u8)]
#[derive(Clone, Debug, PartialEq)]
pub enum SignalSpec {
    S = SIGNAL_S,
    C(usize) = SIGNAL_C,
    M(Shape) = SIGNAL_M,
}

#[repr(u8)]
#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
pub enum Signal {
    S(Scalar) = SIGNAL_S,
    C(Column) = SIGNAL_C,
    M(Matrix) = SIGNAL_M,
}

#[derive(Clone, Debug, PartialEq)]
pub struct Shape {
    // Rows
    channels: usize,
    // Columns
    frames: usize,
}

impl TryFrom<u8> for SignalKind {
    type Error = u8;

    fn try_from(value: u8) -> Result<Self, Self::Error> {
        match value {
            SIGNAL_S | SIGNAL_C | SIGNAL_M => Ok(unsafe { *(&value as *const u8 as *const Self) }),
            _ => Err(value),
        }
    }
}

impl From<SignalKind> for u8 {
    fn from(value: SignalKind) -> Self {
        unsafe { *(&value as *const SignalKind as *const Self) }
    }
}

impl Signal {
    pub fn shape(&self) -> Shape {
        Shape::of(&self)
    }

    pub fn describe(&self) -> SignalSpec {
        SignalSpec::of(&self)
    }

    pub fn kind(&self) -> SignalKind {
        unsafe { *(self as *const Signal as *const u8 as *const SignalKind) }
    }

    pub fn from_vec(kind: &SignalKind, shape: &Shape, data: Vec<Scalar>) -> Result<Self, String> {
        let expected_size = shape.size();
        let actual_size = data.len();
        if expected_size == actual_size {
            match (kind, shape) {
                (
                    SignalKind::S,
                    Shape {
                        channels: 1,
                        frames: 1,
                    },
                ) => Ok(Signal::S(data[0])),
                (SignalKind::C, Shape { frames: 1, .. }) => Ok(Signal::C(Column { data })),
                (SignalKind::M, Shape { channels, .. }) => Ok(Signal::M(Matrix {
                    data: data,
                    channels: *channels,
                })),
                (SignalKind::S, _) => Err(format!("Scalar must have shape 1x1, not {shape}")),
                (SignalKind::C, _) => Err(format!("Column must have shape 1x*, not {shape}")),
            }
        } else {
            Err(format!(
                "Cannot fit {actual_size} elements into shape {shape}"
            ))
        }
    }

    pub fn from_raw(bytes: &[u8]) -> Result<Self, String> {
        use serialization::{Body, Header};

        let header: [u8; Header::SIZE] = bytes[0..Header::SIZE].try_into().map_err(|_| {
            format!(
                "Expected at least {} bytes, found only {}",
                Header::SIZE,
                bytes.len()
            )
        })?;
        let header = Header::from_raw(header)?;
        let data = Body::from_raw(&bytes[Header::SIZE..])?;

        Self::from_vec(&header.kind, &header.shape, data)
    }

    pub fn to_raw(&self) -> Vec<u8> {
        use serialization::{size, Body, Header};

        let header = Header::new(self);
        let mut result = Vec::<u8>::with_capacity(size(&header));
        result.extend_from_slice(&header.to_raw());
        match self {
            Self::S(scalar) => result.extend_from_slice(&scalar.to_le_bytes()),
            Self::C(column) => result.extend(Body::to_raw(&column.data)),
            Self::M(matrix) => result.extend(Body::to_raw(&matrix.data)),
        }
        result
    }
}

impl From<Signal> for Matrix {
    fn from(value: Signal) -> Self {
        let shape = value.shape();
        Self {
            data: value.into(),
            channels: shape.channels,
        }
    }
}

impl From<Signal> for Vec<Scalar> {
    fn from(value: Signal) -> Self {
        match value {
            Signal::S(scalar) => vec![scalar],
            Signal::C(column) => column.data,
            Signal::M(matrix) => matrix.data,
        }
    }
}

impl Shape {
    pub fn scalar() -> Self {
        Self {
            frames: 1,
            channels: 1,
        }
    }

    pub fn of(sig: &Signal) -> Self {
        match sig {
            Signal::S(_) => Shape::scalar(),
            Signal::C(column) => Shape {
                channels: column.data.len(),
                frames: 1,
            },
            Signal::M(matrix) => Shape {
                channels: matrix.channels,
                frames: matrix.data.len() / matrix.channels,
            },
        }
    }

    pub fn size(&self) -> usize {
        self.channels * self.frames
    }
}

impl fmt::Display for Shape {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        // Matrix notation, rows x columns
        write!(f, "{}x{}", self.channels, self.frames)
    }
}

impl SignalSpec {
    pub fn of(sig: &Signal) -> Self {
        match sig {
            Signal::S(_) => Self::S,
            Signal::C(Column { data }) => Self::C(data.len()),
            Signal::M(_) => Self::M(sig.shape()),
        }
    }
}

impl fmt::Display for SignalSpec {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Self::S => write!(f, "S"),
            Self::C(channels) => write!(f, "C({})", channels),
            Self::M(shape) => write!(f, "M({})", shape),
        }
    }
}

mod serialization {
    use crate::signal::{Scalar, Shape, Signal, SignalKind};
    use std::mem::size_of;

    pub struct Header {
        pub kind: SignalKind,
        pub shape: Shape,
    }

    impl Header {
        pub const SIZE: usize = size_of::<u64>() * 3;

        pub fn new(signal: &Signal) -> Self {
            Self {
                kind: signal.kind(),
                shape: signal.shape(),
            }
        }

        pub fn from_raw(bytes: [u8; Self::SIZE]) -> Result<Self, String> {
            let kind = bytes[0];
            let pad: [u8; 7] = bytes[1..8].try_into().unwrap();
            let channels: [u8; 8] = bytes[8..16].try_into().unwrap();
            let frames: [u8; 8] = bytes[16..24].try_into().unwrap();

            let kind: SignalKind = kind
                .try_into()
                .map_err(|_| format!("Expected a signal kind, found {kind}"))?;

            let [0, 0, 0, 0, 0, 0, 0] = pad else {
                return Err(format!(
                    "Expected 7 bytes of zero-padding after kind; found {pad:?}"
                ));
            };
            let channels = usize::from_le_bytes(channels);
            let frames = usize::from_le_bytes(frames);

            Ok(Self {
                kind: kind,
                shape: Shape { channels, frames },
            })
        }

        pub fn to_raw(&self) -> [u8; Self::SIZE] {
            let mut result = [0; Self::SIZE];
            result[0] = self.kind.into();
            result[8..16].copy_from_slice(&self.shape.channels.to_le_bytes());
            result[16..24].copy_from_slice(&self.shape.frames.to_le_bytes());

            result
        }
    }

    pub struct Body;

    impl Body {
        pub const ITEM_SIZE: usize = size_of::<Scalar>();

        pub fn to_raw<'a>(data: &'a Vec<Scalar>) -> impl Iterator<Item = u8> + 'a {
            data.iter().map(|scalar| scalar.to_le_bytes()).flatten()
        }

        pub fn from_raw(bytes: &[u8]) -> Result<Vec<Scalar>, String> {
            if bytes.len() % Self::ITEM_SIZE == 0 {
                let data: Vec<_> = bytes
                    .chunks(Self::ITEM_SIZE)
                    .map(|chunk| Scalar::from_le_bytes(chunk.try_into().unwrap()))
                    .collect();
                Ok(data)
            } else {
                Err(format!(
                    "Expected a multiple of {} bytes; found {}",
                    Self::ITEM_SIZE,
                    bytes.len()
                ))
            }
        }
    }

    pub fn size(header: &Header) -> usize {
        Header::SIZE + header.shape.size() * Body::ITEM_SIZE
    }
}

#[cfg(test)]
mod tests {
    use crate::signal::*;

    #[test]
    fn test_enum_crimes() {
        assert_eq!(SIGNAL_S.try_into(), Ok(SignalKind::S));
        assert_eq!(SIGNAL_C.try_into(), Ok(SignalKind::C));
        assert_eq!(SIGNAL_M.try_into(), Ok(SignalKind::M));

        assert_eq!(<SignalKind as Into<u8>>::into(SignalKind::S), SIGNAL_S);
        assert_eq!(<SignalKind as Into<u8>>::into(SignalKind::C), SIGNAL_C);
        assert_eq!(<SignalKind as Into<u8>>::into(SignalKind::M), SIGNAL_M);

        assert_eq!(TryInto::<SignalKind>::try_into(0 as u8), Err(0 as u8));

        assert_eq!(SignalKind::S, Signal::S(0.0).kind());
        assert_eq!(SignalKind::C, Signal::C(Column { data: vec![0.0] }).kind());
        assert_eq!(
            SignalKind::M,
            Signal::M(Matrix {
                channels: 1,
                data: vec![0.0]
            })
            .kind()
        );
    }

    #[test]
    fn test_scalar_methods() {
        let scalar = 1.2345;
        let data = vec![scalar];
        let sig = Signal::S(scalar);
        assert_eq!(
            sig.shape(),
            Shape {
                channels: 1,
                frames: 1,
            },
        );
        assert_eq!(
            <Signal as Into<Matrix>>::into(sig.clone()),
            Matrix {
                channels: 1,
                data: data.clone()
            }
        );
        assert_eq!(<Signal as Into<Vec<Scalar>>>::into(sig.clone()), data);

        test_recover_raw(
            &sig,
            b"s\0\0\0_\0\0\0\0_\x01\0\0\0_\0\0\0\0_\x01\0\0\0_\0\0\0\0_\x19\x04\x9e\x3f",
        );
    }

    #[test]
    fn test_column_methods() {
        let data = vec![1.2, 3.4, 5.6];
        let column = Column { data: data.clone() };
        let sig = Signal::C(column);
        assert_eq!(
            sig.shape(),
            Shape {
                channels: 3,
                frames: 1,
            },
        );
        assert_eq!(
            <Signal as Into<Matrix>>::into(sig.clone()),
            Matrix {
                channels: 3,
                data: data.clone()
            }
        );
        assert_eq!(<Signal as Into<Vec<Scalar>>>::into(sig.clone()), data);

        test_recover_raw(&sig, b"c\0\0\0_\0\0\0\0_\x03\0\0\0_\0\0\0\0_\x01\0\0\0_\0\0\0\0_\x9a\x99\x99\x3f_\x9a\x99\x59\x40_\x33\x33\xb3\x40");
    }

    #[test]
    fn test_matrix_methods() {
        let data = vec![1.2, 3.4, 5.6, 7.8];
        let matrix = Matrix {
            channels: 2,
            data: data.clone(),
        };
        let sig = Signal::M(matrix.clone());
        assert_eq!(
            sig.shape(),
            Shape {
                channels: 2,
                frames: 2,
            },
        );
        assert_eq!(<Signal as Into<Matrix>>::into(sig.clone()), matrix);
        assert_eq!(<Signal as Into<Vec<Scalar>>>::into(sig.clone()), data);

        test_recover_raw(&sig, b"m\0\0\0_\0\0\0\0_\x02\0\0\0_\0\0\0\0_\x02\0\0\0_\0\0\0\0_\x9a\x99\x99\x3f_\x9a\x99\x59\x40_\x33\x33\xb3\x40_\x9a\x99\xf9\x40");
    }

    fn test_recover_raw(sig: &Signal, bytes_with_sep: &[u8]) {
        let raw: Vec<u8> = sig.to_raw();
        let expected = strip_separator(bytes_with_sep);
        assert_eq!(raw, expected);
        assert_eq!(Signal::from_raw(&raw), Ok(sig.clone()));
    }

    fn strip_separator(with_sep: &[u8]) -> Vec<u8> {
        let mut bytes = with_sep.to_vec();
        bytes.retain(|&b| b != b'_');
        bytes
    }
}
