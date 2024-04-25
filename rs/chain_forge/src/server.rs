use std::io::{Read, Write};
use std::net::TcpListener;
use std::os::unix::net::UnixListener;

use log::{error, info, warn};

use crate::api::Api;
use crate::http::{read_request, write_response};

const SOCKET_PATH: &'static str = "/tmp/chainforge.sock";
const TCP_IP_ADDRESS: &'static str = "127.0.0.1:7878";

pub struct Server {
    api: Api,
}

impl Server {
    pub fn new() -> Self {
        Self { api: Api::new() }
    }

    pub fn serve_unix(&mut self) -> std::io::Result<()> {
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

    pub fn serve_tcp(&mut self) -> std::io::Result<()> {
        let listener = TcpListener::bind(TCP_IP_ADDRESS)?;
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
                self.api.route(&request)
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
}
