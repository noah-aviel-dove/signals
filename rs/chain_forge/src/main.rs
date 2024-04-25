use chain_forge::server::Server;
use std::io::Result;

fn main() -> std::io::Result<()> {
    let mut server = Server::new();
    server.serve_tcp()
}
