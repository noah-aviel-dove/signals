use std::collections::HashMap;
use std::str::FromStr;

use serde::{Deserialize, Serialize};

use mime::Mime;

use http::header::HeaderName;
use http::Method;

use rmp_serde;
use serde_json;

use crate::http::responses::{
    bad_method, bad_request, cant_accept, created, json, msgpack, no_content, not_found, ok, ok_txt,
};
use crate::http::{Request, Response};
use crate::Id;

use crate::service::chain::spec::{ChainSpec, LinkSpec};
use crate::service::chain::Chain;
use crate::signal::Signal;

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
            .map_err(|err| bad_request(format!("Failed to decode JSON: {err}")))
    } else if content_type == Some(mime::APPLICATION_JSON) {
        serde_json::from_slice::<T>(&body)
            .map_err(|err| bad_request(format!("Failed to decode MSGPACK: {err}")))
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
    Ok(bad_method(&[Method::HEAD, Method::GET]))
}

fn allow_get_put_del() -> TryResponse {
    Ok(bad_method(&[
        Method::HEAD,
        Method::GET,
        Method::PUT,
        Method::DELETE,
    ]))
}

struct ChainApi {
    mesh: HashMap<Id, Chain>,
}

impl<'a> ChainApi {
    pub fn new() -> Self {
        Self {
            mesh: HashMap::<_, _>::new(),
        }
    }

    pub fn list(&self) -> Vec<Id> {
        self.mesh.keys().copied().collect::<Vec<_>>()
    }

    pub fn get(&self, id: Id) -> Option<ChainSpec> {
        let chain = self.mesh.get(&id)?;
        Some(chain.describe())
    }

    pub fn put(&mut self, id: Id, spec: ChainSpec) -> bool {
        let chain = spec.reify();
        self.mesh.insert(id, chain).is_some()
    }

    pub fn del(&mut self, id: Id) -> bool {
        self.mesh.remove(&id).is_some()
    }

    pub fn get_links(&self, id: Id) -> Option<Vec<LinkSpec>> {
        let chain = self.mesh.get(&id)?;
        Some(chain.describe_links())
    }

    pub fn get_link(&self, id: Id, index: usize) -> Option<LinkSpec> {
        let link: &_ = self.mesh.get(&id)?.links.get(index)?;
        Some(link.describe())
    }

    pub fn get_vars(&'a self, id: Id) -> Option<&'a Vec<Signal>> {
        let chain = self.mesh.get(&id)?;
        Some(&chain.vars)
    }

    pub fn get_var(&'a self, id: Id, index: usize) -> Option<&'a Signal> {
        let var = self.mesh.get(&id)?.vars.get(index)?;
        Some(&var)
    }

    pub fn patch_var(
        &mut self,
        id: Id,
        index: usize,
        new_var: Signal,
    ) -> Option<Result<(), String>> {
        let var = self.mesh.get_mut(&id)?.vars.get_mut(index)?;
        let old_spec = var.describe();
        let new_spec = new_var.describe();
        if old_spec == new_spec {
            *var = new_var;
            Some(Ok(()))
        } else {
            Some(Err(format!("Cannot patch {old_spec} with {new_spec}")))
        }
    }
}
