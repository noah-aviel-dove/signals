use std::io::{BufWriter, Read, Write};
use std::os::unix::net::UnixListener;

use http;
use http::header::HeaderValue;
use http::method::Method;
use http::status::StatusCode;
use httparse;

use log::{error, info, warn};

const SOCKET_PATH: &'static str = "/tmp/chainforge.sock";

type Request<'a> = http::request::Request<Vec<u8>>;
type Response = http::response::Response<Vec<u8>>;

struct ChainService;
struct SequenceService;
struct DataService;

impl ChainService {
    fn put(&mut self, request: &Request) -> Response {
        http::response::Builder::new()
            .status(200)
            .body(b"hey there".into())
            .unwrap()
    }
}

pub struct Server {
    chain_service: ChainService,
    sequence_service: SequenceService,
    data_service: DataService,
}

impl Server {
    pub fn new() -> Self {
        Self {
            chain_service: ChainService {},
            sequence_service: SequenceService {},
            data_service: DataService {},
        }
    }

    pub fn serve(&mut self) -> std::io::Result<()> {
        let listener = UnixListener::bind(SOCKET_PATH)?;
        for stream in listener.incoming() {
            match stream {
                Ok(stream) => self.handle_connection(stream),
                Err(err) => error!("Unable to read connection: {err}"),
            }
        }
        // Never reached
        Ok(())
    }

    fn handle_connection<RW: Read + Write>(&mut self, mut stream: RW) {
        let request = read_request(&mut stream);
        let mut response = match request {
            Ok(request) => {
                let (method, path) = (request.method(), request.uri().path());
                info!("Read request: {method} {path}");
                self.handle_request(&request)
            }
            Err(response) => {
                let status = response.status();
                warn!("Failed to read request: {status}");
                response
            }
        };
        let result = write_response(&mut stream, &mut response);
        match result {
            Ok(()) => {
                let status = response.status();
                info!("Wrote response: {status}");
            }
            Err(err) => {
                error!("Failed to write response: {err}");
            }
        }
    }

    fn handle_request(&mut self, request: &Request) -> Response {
        match request.uri().path() {
            "/" => Response::new(b"Hello world".into()),
            "/chain" => match request.method() {
                &Method::PUT => self.chain_service.put(request),
                _ => bad_method(&[Method::PUT]),
            },
            _ => not_found(),
        }
    }
}

fn read_request<R: Read>(stream: &mut R) -> Result<Request, Response> {
    let mut headers = [httparse::EMPTY_HEADER; 16];
    let mut parsing_request = httparse::Request::new(&mut headers);
    const max_head_size: usize = 1024;
    let mut buf = vec![0 as u8; max_head_size];
    let mut read = 0;

    // For now, for sanity's sake, I'm going to assume this doesn't hang when there are less than
    // 1024 bytes in the stream...
    // Good news, it doesn't hang. Bad news, it returns `Err` instead.
    // What the actual fuck is this shit.
    match stream.read(&mut buf[..]) {
        Err(err) => Err(internal_error(
            format!("Failed to read request: {}", err).as_bytes(),
        )),
        Ok(0) => Err(bad_request(b"Empty request")),
        Ok(newly_read) => {
            read += newly_read;
            match parsing_request.parse(&buf) {
                Err(err) => Err(bad_request(
                    format!("Bad request syntax: {}", err).as_bytes(),
                )),
                Ok(httparse::Status::Partial) => Err(bad_request(
                    format!(
                    "Request head too large; body not found after reading {max_head_size} bytes"
                )
                    .as_bytes(),
                )),
                Ok(httparse::Status::Complete(body_start)) => {
                    assert!(body_start <= read);
                    let mut builder = http::Request::builder();
                    builder = parsing_request
                        .headers
                        .iter()
                        .fold(builder, |builder, header| {
                            builder.header(header.name, header.value)
                        })
                        .method(parsing_request.method.unwrap())
                        .uri(parsing_request.path.unwrap())
                        .version(match parsing_request.version.unwrap() {
                            0 => http::version::Version::HTTP_10,
                            1 => http::version::Version::HTTP_11,
                            v => panic!(
                                "httparse should have reported an error for HTTP version {v}"
                            ),
                        });

                    let method = builder.method_ref().unwrap();
                    if let &Method::PUT | &Method::POST | &Method::PATCH = method {
                        let headers = builder.headers_ref().unwrap();
                        match headers.get(http::header::CONTENT_LENGTH) {
                            None => return Err(length_required()),
                            Some(content_length) => {
                                let content_length = content_length.to_str().unwrap();
                                match content_length.parse::<usize>() {
                                    Ok(content_length) => {
                                        buf.resize(body_start + content_length, 0);
                                        if let Err(err) = stream.read_exact(&mut buf[body_start..])
                                        {
                                            return Err(internal_error(
                                                format!("Failed to read request: {}", err)
                                                    .as_bytes(),
                                            ));
                                        }
                                    }
                                    Err(_) => {
                                        return Err(bad_request(
                                            format!(
                                                "Non-numerical content length: {content_length}"
                                            )
                                            .as_bytes(),
                                        ))
                                    }
                                }
                            }
                        }
                    }
                    buf = buf[body_start..].into();
                    Ok(builder.body(buf).unwrap())
                }
            }
        }
    }
}

fn write_response<W: Write>(stream: &mut W, response: &mut Response) -> std::io::Result<()> {
    let version = response.version();
    let status = response.status();
    let content_length = response.body().len();
    response.headers_mut().append(
        http::header::CONTENT_LENGTH,
        HeaderValue::from_str(content_length.to_string().as_str()).unwrap(),
    );

    let mut writer = BufWriter::new(stream);
    writer.write(format!("{version:?} {status}\r\n").as_bytes())?;

    for (key, value) in response.headers().iter() {
        writer.write(key.as_ref())?;
        writer.write(b": ")?;
        writer.write(value.as_ref())?;
        writer.write(b"\r\n")?;
    }
    writer.write(b"\r\n")?;
    writer.write(response.body())?;
    writer.write(b"\r\n\r\n")?;
    writer.flush()?;
    Ok(())
}

fn bad_request(body: &[u8]) -> Response {
    http::response::Builder::new()
        .status(StatusCode::BAD_REQUEST)
        .body(body.into())
        .unwrap()
}

fn not_found() -> Response {
    http::response::Builder::new()
        .status(StatusCode::NOT_FOUND)
        .body(b"".into())
        .unwrap()
}

fn bad_method(allow: &[http::Method]) -> Response {
    let builder = http::response::Builder::new();
    allow
        .iter()
        .fold(builder, |builder, method| {
            builder.header(http::header::ALLOW, method.as_str())
        })
        .status(StatusCode::METHOD_NOT_ALLOWED)
        .body(b"".into())
        .unwrap()
}

fn length_required() -> Response {
    http::response::Builder::new()
        .status(StatusCode::LENGTH_REQUIRED)
        .body(b"".into())
        .unwrap()
}

fn internal_error(body: &[u8]) -> Response {
    http::response::Builder::new()
        .status(StatusCode::INTERNAL_SERVER_ERROR)
        .body(body.into())
        .unwrap()
}

#[cfg(test)]
mod tests {
    use crate::server::*;

    #[test]
    fn test_write_response() {
        let mut buf = Vec::<u8>::new();

        {
            let mut response = bad_request(b"Oh no! Discombobulated splines!");
            write_response(&mut buf, &mut response);
        }
        
        let expected = b"HTTP/1.1 400 Bad Request\r\ncontent-length: 31\r\n\r\nOh no! Discombobulated splines!\r\n\r\n".to_vec();
        assert_eq!(buf, expected);
    }

    #[test]
    fn test_read_request() {
        let body = "According to all known laws of aviation,";
        let content_length = body.len();
        let request = format!("POST /foo/bar HTTP/1.1\r\ncontent-length: {content_length}\r\n\r\n{body}");
        let read = read_request(&mut request.as_bytes()).unwrap();

        assert_eq!(read.method(), Method::POST);
        assert_eq!(format!("{}", read.uri()), "/foo/bar");
        assert_eq!(
            read.headers().get(http::header::ACCEPT),
            Some(&HeaderValue::from_static("*/*"))
        );
        assert_eq!(read.body(), b"According to all known laws\r\nof aviation,");
    }
}
