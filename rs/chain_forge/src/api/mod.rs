mod chain;

use std::str::FromStr;

use serde::{Deserialize, Serialize};

use mime::Mime;

use http::header::HeaderName;
use http::Method;

use rmp_serde;
use serde_json;

use crate::chain::ChainSpec;
use crate::http::responses::{
    bad_method, bad_request, cant_accept, created, json, msgpack, no_content, not_found, ok, ok_txt,
};
use crate::http::{Request, Response};
use crate::Id;

use crate::api::chain::ChainApi;

pub struct Api {
    chains: ChainApi,
}

// `Err` means we wanted to short-circuit out of handling the request early,
// usually due to either a server error or client error
type TryResponse = Result<Response, Response>;

impl Api {
    pub fn new() -> Self {
        Self {
            chains: ChainApi::new(),
        }
    }

    pub fn route(&mut self, request: &Request) -> Response {
        match self.inner_route(&request) {
            Ok(response) => response,
            Err(response) => response,
        }
    }

    fn inner_route(&mut self, request: &Request) -> TryResponse {
        let parts = request.uri().path().split("/").collect::<Vec<_>>();
        let method = request.method();
        let content_type: Option<Mime> = parse_header(&request, &http::header::CONTENT_TYPE);
        let accepts: Option<Mime> = parse_header(&request, &http::header::ACCEPT);
        match &parts[..] {
            ["", ""] => match method {
                &Method::HEAD => Ok(ok()),
                &Method::GET => Ok(ok_txt("Hello world".into())),
                _ => allow_get(),
            },
            ["", "chains"] => match method {
                &Method::HEAD => Ok(ok()),
                &Method::GET => Ok(negotiate_output(accepts, &self.chains.list())),
                _ => allow_get(),
            },
            ["", "chain", id] => {
                let id: Id = route_var(id)?;
                match method {
                    &Method::HEAD => wrap_head(self.chains.get(id)),
                    &Method::GET => wrap_get(accepts, self.chains.get(id)),
                    &Method::PUT => {
                        let spec: ChainSpec = negotiate_input(content_type, request.body())?;
                        wrap_put(self.chains.put(id, spec))
                    }
                    &Method::DELETE => wrap_del(self.chains.del(id)),
                    _ => allow_get_put_del(),
                }
            }
            ["", "chain", id, "links"] => {
                let id: Id = route_var(id)?;
                match method {
                    &Method::HEAD => wrap_head(self.chains.get_links(id)),
                    &Method::GET => wrap_get(accepts, self.chains.get_links(id)),
                    _ => allow_get(),
                }
            }
            ["", "chain", id, "link", index] => {
                let id: Id = route_var(id)?;
                let index: usize = route_var(index)?;
                match method {
                    &Method::HEAD => wrap_head(self.chains.get_link(id, index)),
                    &Method::GET => wrap_get(accepts, self.chains.get_link(id, index)),
                    _ => allow_get(),
                }
            }
            ["", "chain", id, "vars"] => {
                let id: Id = route_var(id)?;
                match method {
                    &Method::HEAD => wrap_head(self.chains.get_vars(id)),
                    &Method::GET => wrap_get(accepts, self.chains.get_vars(id)),
                    _ => allow_get(),
                }
            }
            ["", "chain", id, "var", index] => {
                let id: Id = route_var(id)?;
                let index: usize = route_var(index)?;
                match method {
                    &Method::HEAD => wrap_head(self.chains.get_var(id, index)),
                    &Method::GET => wrap_get(accepts, self.chains.get_var(id, index)),
                    _ => allow_get(),
                }
            }
            _ => Err(not_found()),
        }
    }
}

pub fn parse_header<T: FromStr>(request: &Request, key: &HeaderName) -> Option<T> {
    // Deliberately very sloppy
    request
        .headers()
        .get(key)?
        .to_str()
        .ok()?
        .split(",")
        .next()?
        .parse::<T>()
        .ok()
}

fn negotiate_output<T>(accepts: Option<Mime>, result: &T) -> Response
where
    T: Serialize,
{
    if accepts == Some(mime::APPLICATION_MSGPACK) {
        msgpack(result)
    } else {
        json(result)
    }
}

fn negotiate_input<T>(content_type: Option<Mime>, body: &[u8]) -> Result<T, Response>
where
    T: for<'a> Deserialize<'a>,
{
    if content_type == Some(mime::APPLICATION_MSGPACK) {
        rmp_serde::from_slice::<T>(&body)
            .map_err(|err| bad_request(format!("Failed to decode MSGPACK: {err}")))
    } else if content_type == Some(mime::APPLICATION_JSON) {
        serde_json::from_slice::<T>(&body)
            .map_err(|err| bad_request(format!("Failed to decode JSON: {err}")))
    } else {
        Err(cant_accept(&[
            mime::APPLICATION_MSGPACK,
            mime::APPLICATION_JSON,
        ]))
    }
}

fn route_var<T: FromStr>(raw: &str) -> Result<T, Response>
where
    <T as FromStr>::Err: std::fmt::Display,
{
    raw.parse::<T>()
        .map_err(|err| bad_request(format!("Invalid URL element `{raw}`: {err}")))
}

fn wrap_head<T>(result: Option<T>) -> TryResponse {
    Ok(result.map_or_else(not_found, |_| ok()))
}

fn wrap_get<T: Serialize>(accepts: Option<Mime>, result: Option<T>) -> TryResponse {
    Ok(result.map_or_else(not_found, |result| negotiate_output(accepts, &result)))
}

fn wrap_put(already_present: bool) -> TryResponse {
    Ok(if already_present {
        no_content()
    } else {
        created()
    })
}

fn wrap_del(was_present: bool) -> TryResponse {
    Ok(if was_present {
        no_content()
    } else {
        not_found()
    })
}

fn allow_get() -> TryResponse {
    Err(bad_method(&[Method::HEAD, Method::GET]))
}

fn allow_get_put_del() -> TryResponse {
    Err(bad_method(&[
        Method::HEAD,
        Method::GET,
        Method::PUT,
        Method::DELETE,
    ]))
}
