use std::io::{BufWriter, Read, Write};

use http;
use http::header::HeaderValue;
use http::header::CONTENT_LENGTH;
use http::version::Version;

use httparse;

pub type Request = http::request::Request<Vec<u8>>;
pub type Response = http::response::Response<Vec<u8>>;

const MAX_REQUEST_HEAD_SIZE: usize = 1024;

pub fn read_request<R: Read>(stream: &mut R) -> Result<Request, Response> {
    let mut headers = [httparse::EMPTY_HEADER; 16];
    let mut parsing_request = httparse::Request::new(&mut headers);
    let mut buf = vec![0 as u8; MAX_REQUEST_HEAD_SIZE];
    let mut read = 0;

    match stream.read(&mut buf[..]) {
        Err(err) => Err(responses::internal_error(format!(
            "Failed to read request head: {}",
            err
        ))),
        Ok(0) => Err(responses::bad_request("Empty request".into())),
        Ok(newly_read) => {
            read += newly_read;
            match parsing_request.parse(&buf) {
                Err(err) => Err(responses::bad_request(
                    format!("Bad request syntax: {}", err),
                )),
                Ok(httparse::Status::Partial) => Err(responses::bad_request(
                    format!("Request head too large; body not found after reading {MAX_REQUEST_HEAD_SIZE} bytes")
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
                            0 => Version::HTTP_10,
                            1 => Version::HTTP_11,
                            v => panic!("httparse should have reported an error for HTTP version {v}"),
                        });

                    let headers = builder.headers_ref().unwrap();
                    let content_length = match headers.get(CONTENT_LENGTH) {
                        None => 0,
                        Some(content_length) => {
                            let content_length = content_length.to_str().unwrap();
                            match content_length.parse::<usize>() {
                                Ok(content_length) => content_length,
                                Err(err) => {
                                    return Err(responses::bad_request(
                                        format!("Failed to read content length: {err}")
                                    ))
                                }
                            }
                        }
                    };
                    buf.resize(body_start + content_length, 0);
                    if let Err(err) = stream.read_exact(&mut buf[read..]) {
                        return Err(responses::internal_error(
                            format!("Failed to read request body: {err}")
                        ));
                    }
                    let body = buf[body_start..].into();
                    Ok(builder.body(body).unwrap())
                }
            }
        }
    }
}

pub fn write_response<W: Write>(stream: &mut W, response: &mut Response) -> std::io::Result<()> {
    let version = response.version();
    let status = response.status();
    let content_length = response.body().len();
    response.headers_mut().append(
        CONTENT_LENGTH,
        HeaderValue::from_str(content_length.to_string().as_str()).unwrap(),
    );

    let mut writer = BufWriter::new(stream);
    writer.write(&format!("{version:?} {status}\r\n").into_bytes())?;

    for (key, value) in response.headers().iter() {
        writer.write(key.as_ref())?;
        writer.write(b": ")?;
        writer.write(value.as_ref())?;
        writer.write(b"\r\n")?;
    }
    writer.write(b"\r\n")?;
    writer.write(response.body())?;
    writer.flush()?;
    Ok(())
}

pub mod responses {

    use http::status::StatusCode;
    use mime::Mime;
    use rmp_serde;
    use serde::Serialize;
    use serde_json;

    use crate::http::Response;

    pub fn json<T: Serialize>(body: &T) -> Response {
        match serde_json::to_vec(&body) {
            Ok(bytes) => new(StatusCode::OK, bytes, mime::APPLICATION_JSON),
            Err(err) => internal_error(format!("Error serializing JSON response: {err}")),
        }
    }

    pub fn msgpack<T: Serialize>(body: &T) -> Response {
        match rmp_serde::to_vec(&body) {
            Ok(bytes) => new(StatusCode::OK, bytes, mime::APPLICATION_MSGPACK),
            Err(err) => internal_error(format!("Error serializing MSGPACK response: {err}")),
        }
    }

    pub fn ok() -> Response {
        empty(StatusCode::OK)
    }

    pub fn ok_txt(msg: String) -> Response {
        new(StatusCode::OK, msg.into_bytes(), mime::TEXT_PLAIN_UTF_8)
    }

    pub fn created() -> Response {
        empty(StatusCode::CREATED)
    }

    pub fn no_content() -> Response {
        empty(StatusCode::NO_CONTENT)
    }

    pub fn bad_request(body: String) -> Response {
        new(
            StatusCode::BAD_REQUEST,
            body.into_bytes(),
            mime::TEXT_PLAIN_UTF_8,
        )
    }

    pub fn not_found() -> Response {
        empty(StatusCode::NOT_FOUND)
    }

    pub fn bad_method(allow: &[http::Method]) -> Response {
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

    pub fn length_required() -> Response {
        empty(StatusCode::LENGTH_REQUIRED)
    }

    pub fn cant_accept(allow: &[Mime]) -> Response {
        let builder = http::response::Builder::new();
        allow
            .iter()
            .fold(builder, |builder, mime| {
                builder.header(http::header::ACCEPT, mime.essence_str())
            })
            .status(StatusCode::UNSUPPORTED_MEDIA_TYPE)
            .body("".into())
            .unwrap()
    }

    pub fn bad_entity(body: String) -> Response {
        new(
            StatusCode::UNPROCESSABLE_ENTITY,
            body.into_bytes(),
            mime::TEXT_PLAIN_UTF_8,
        )
    }

    pub fn internal_error(body: String) -> Response {
        new(
            StatusCode::INTERNAL_SERVER_ERROR,
            body.into_bytes(),
            mime::TEXT_PLAIN_UTF_8,
        )
    }

    pub fn not_implemented() -> Response {
        empty(StatusCode::NOT_IMPLEMENTED)
    }

    pub fn empty(status: StatusCode) -> Response {
        http::response::Builder::new()
            .status(status)
            .body(b"".into())
            .unwrap()
    }

    pub fn new(status: StatusCode, body: Vec<u8>, content_type: Mime) -> Response {
        http::response::Builder::new()
            .status(status)
            .header(http::header::CONTENT_TYPE, content_type.essence_str())
            .body(body)
            .unwrap()
    }
}

#[cfg(test)]
mod tests {
    use crate::http::responses::*;
    use crate::http::*;

    use http::header::CONTENT_LENGTH;
    use http::{HeaderValue, Method};

    #[test]
    fn test_write_response() {
        let mut buf = Vec::<u8>::new();

        {
            let mut response = bad_request("Oh no! Discombobulated splines!".into());
            write_response(&mut buf, &mut response).unwrap();
        }

        let expected = b"HTTP/1.1 400 Bad Request\r\ncontent-type: text/plain\r\ncontent-length: 31\r\n\r\nOh no! Discombobulated splines!".to_vec();
        assert_eq!(buf, expected);
    }

    #[test]
    fn test_read_small_request() {
        let request = b"POST /foo/bar HTTP/1.1\r\ncontent-length: 40\r\n\r\nAccording to all known laws of aviation,";
        let read = read_request(&mut request.as_ref()).unwrap();

        assert_eq!(read.method(), Method::POST);
        assert_eq!(format!("{}", read.uri()), "/foo/bar");
        assert_eq!(
            read.headers().get(CONTENT_LENGTH),
            Some(&HeaderValue::from_static("40"))
        );
        assert_eq!(read.body(), b"According to all known laws of aviation,");
    }

    #[test]
    fn test_read_large_request() {
        const BODY_SIZE: usize = 12345;
        let body = vec![b'A'; BODY_SIZE];
        let request = format!(
            "POST /foo/bar HTTP/1.1\r\ncontent-length: {BODY_SIZE}\r\n\r\n{}",
            String::from_utf8(body.clone()).unwrap()
        );
        let read = read_request::<&[u8]>(&mut request.as_ref()).unwrap();

        assert_eq!(read.method(), Method::POST);
        assert_eq!(format!("{}", read.uri()), "/foo/bar");
        assert_eq!(
            read.headers().get(CONTENT_LENGTH),
            Some(&HeaderValue::from_str(&BODY_SIZE.to_string()).unwrap())
        );
        assert_eq!(read.into_body(), body);
    }
}
