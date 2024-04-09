use std::io::{BufRead, BufReader, Read, Write};
use std::os::unix::net::UnixListener;

use http;
use http::method::Method;
use http::status::StatusCode;
use http::header::HeaderValue;
use httparse;

use log::{error, info, warn};

const SOCKET_PATH: &'static str = "/tmp/chainforge.sock";

type Response = http::response::Response<String>;
type Request = http::request::Request<String>;

struct ChainService;
struct SequenceService;
struct DataService;

impl ChainService {
    fn put(&mut self, request: &Request) -> Response {
        http::response::Builder::new()
            .status(200)
            .body(String::new())
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
            "/" => Response::new("Hello world".into()),
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
    let mut buf = Vec::<u8>::new();
    let mut offset = 0;
    let mut block_size = 64;
    loop {
        buf.resize(buf.len() + buf_size);
        buf_size *= 2;
        match stream.read(&mut buf[offset..]) {
            Err(err) => return Err(internal_error(format!("Failed to read request: {}", err))),
            Ok(0) => return Err(bad_request("Incomplete or malformed request".to_string())),
            Ok(read) => {
                offset += read;
                match parsing_request.parse(buf) {
                    Err(err) => return Err(bad_request(format!("Failed to parse request: {}", err))),
                    Ok(httparse::Status::Partial) => {
                        continue;
                    },
                    Ok(httparse::Status::Complete(final_offset)) => {
                        assert!(final_offset <= offset);
                        offset = final_offset;
                        break;
                    },
                }
            }
        }
    }

    let mut builder = http::Request::builder();
    builder = parsing_request.headers.iter()
        .fold(builder, |builder, header| builder.header(header.name, header.value))
        .method(parsing_request.method.unwrap())
        .uri(parsing_request.path.unwrap())
        .version(match parsing_request.version.unwrap() {
            0 => http::verison::HTTP_10,
            1 => http::version::HTTP_11,
            v => panic!("httparse should have reported an error for HTTP version {v}"),
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
                        let mut bytes = vec![0; content_length];
                        match stream.read_exact(&mut bytes) {
                            Err(err) => {return Err(internal_error(format!("Failed to read request: {}", err)))},
                            Ok(_) => {buf = String::from_utf8(bytes).unwrap();}
                        }
                    }
                    Err(_) => { return Err(bad_request(format!("Non-numerical content length: {content_length}"))) },
                }
            }
        }
    
    match reader.read_line(&mut buf) {
        Ok(0) =>  Err(bad_request("Empty or malformed request".to_string())),
        Ok(_) => 

                let mut builder = http::Request::builder()
                    // Omitting version because httparse only supports 1.0 and 1.1


                loop {
                    buf.clear();
                    match reader.read_line(&mut buf) {
                        Err(err) => return Err(internal_error(format!("Failed to read request: {}", err))),
                        Ok(0) => break,
                        Ok(_) => match buf.split_once(":") {
                            None => return Err(bad_request(format!("Malformed header: {}", buf))),
                            Some((name, value)) => {
                                builder = builder.header(name, value.trim_start());
                            },
                        },
                    }
                }


                } else {
                    buf.clear();
                }

                Ok(builder
                    .body(buf)
                    .unwrap())
            }
        },
    }
}


fn write_response<W: Write>(stream: &mut W, response: &mut Response) -> std::io::Result<()> {
    let version = response.version();
    let status = response.status();
    let line = format!("{version:?} {status}\r\n");
    stream.write_all(line.as_bytes())?;
    let content_length = response.body().len();
    response.headers_mut().append(
        http::header::CONTENT_LENGTH,
        HeaderValue::from_str(content_length.to_string().as_str()).unwrap()
    );
    for (key, value) in response.headers().iter() {
        let value = value.to_str().expect("Non-UTF8 value in header");
        let line = format!("{key}: {value}\r\n");
        stream.write_all(line.as_bytes())?;
    }
    stream.write_all(b"\r\n")?;
    stream.write_all(response.body().as_bytes())?;
    stream.write_all(b"\r\n\r\n")?;
    Ok(())
}

fn bad_request(body: String) -> Response {
    http::response::Builder::new()
        .status(StatusCode::BAD_REQUEST)
        .body(body)
        .unwrap()
}

fn not_found() -> Response {
    http::response::Builder::new()
        .status(StatusCode::NOT_FOUND)
        .body(String::new())
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
        .body(String::new())
        .unwrap()
}

fn length_required() -> Response {
    http::response::Builder::new()
        .status(StatusCode::LENGTH_REQUIRED)
        .body(String::new())
        .unwrap()
}

fn internal_error(body: String) -> Response {
    http::response::Builder::new()
        .status(StatusCode::INTERNAL_SERVER_ERROR)
        .body(body)
        .unwrap()
}

#[cfg(test)]
mod tests {
    use crate::server::*;

    #[test]
    fn test_write_response() {
        let message = "Oh no! Discombobulated splines!";
        let mut buf = Vec::<u8>::new();
        
        {
            let mut response = bad_request(message.to_string());
            write_response(&mut buf, &mut response);
        }

        let written = std::str::from_utf8(buf.as_slice()).unwrap().to_string();
        assert_eq!(written, "HTTP/1.1 400 Bad Request\r\ncontent-length: 31\r\n\r\nOh no! Discombobulated splines!\r\n\r\n");
    }
    

    #[test]
    fn test_read_request() {
        let mut request = "POST /foo/bar HTTP/1.1\r\naccept: */*\r\n\r\nAccording\r\nto all known laws\r\nof aviation,\r\n\r\n".as_bytes();
        let read = read_request(&mut request).unwrap();

        assert_eq!(read.method(), Method::POST);
        assert_eq!(format!("{}", read.uri()), "/foo/bar");
        assert_eq!(read.headers().get(http::header::ACCEPT), Some(&HeaderValue::from_static("*/*")));
        assert_eq!(read.body(), "According to all known laws\r\nof aviation,");
    }
}
