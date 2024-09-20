use chain_forge::server::Server;

fn main() -> std::io::Result<()> {
    let mut server = Server::new();
    server.serve_tcp()
}
