use crate::http::errors::{bad_method, bad_request, not_found, not_implemented};
use crate::http::{Request, Response};

pub struct Api {}

impl Api {
    pub fn new() -> Self {
        Self {}
    }

    pub fn route(&mut self, request: &Request) -> Response {
        let parts = request.uri().path().split("/").collect::<Vec<_>>();
        assert_eq!(parts[0], "");
        match &parts[1..] {
            ["chain", id] => match request.method() {
                &http::Method::PUT => self.put_chain(id, &request.body()),
                _ => bad_method(&[http::Method::PUT]),
            },
            _ => not_found(),
        }
    }

    fn put_chain(&mut self, chain_id: &str, chain_body: &Vec<u8>) -> Response {
        match chain_id.parse::<u64>() {
            Err(err) => bad_request(format!("Invalid chain ID '{chain_id}': {err}").into_bytes()),
            Ok(chain_id) => not_implemented(),
        }
    }
}
