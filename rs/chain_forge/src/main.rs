mod api;
mod http;
mod server;
mod signal;

use crate::server::Server;

fn main() {
    let mut server = Server::new();
    server.serve();
}
