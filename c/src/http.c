#include "http.h"


int read_request(int, struct http_request);

void respond(int, struct http_status, char*);



int server_fd = -1;

struct sockaddr_un server_addr;

const char server_path[] = "chainforge_sock";


void server_init(void) {
    server_fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (server_fd < 0) {
        perror("Failed to create socket");
        exit(EXIT_FAILURE);
    }

    server_addr.sun_family = AF_UNIX;
    assert(sizeof(server_path) < sizeof(server_addr.sun_path));
    strcpy(server_addr.sun_path, server_path);

    if (bind(server_fd, (struct sockaddr*)&server_addr, SUN_LEN(&server_addr)) < 0) {
        perror("Failed to bind server address");
        exit(EXIT_FAILURE);
    }

    if (listen(server_fd, 10) < 0) {
        perror("Failed to listen");
        exit(EXIT_FAILURE);
    }
}


void server_run(void) {
    int client_fd;
    struct sockaddr_un client_addr;
    socklen_t client_addr_len = sizeof(client_addr);
    while (1) {
        client_fd = accept(server_fd, (struct sockaddr*)&client_addr, &client_addr_len);
        if (client_fd < 0) {
            perror("Failed to accept client connection");
        } else {
            struct http_request request;
            if (!read_request(client_fd, &request)) {
                
            }
            close(client_fd);
            free(request);
        }
    }
}


int read_request(int fd, struct http_request *request) {
    const size_t msg_size[2] = {1024, 1024 * 1024};
    char *msg = malloc(buff_size[0]);
    ssize_t received_size = recv(fd, msg, msg_size[0], MSG_PEEK);
    if (received_size < msg_size[0]) {
        if (received_size <= 0) {
            perror("Failed to read request");
            free(msg);
            return 1;
        }
        recv(client_fd, msg, 0);
    } else {
        msg = realloc(msg, msg_size[1]);
        received_size = recv(fd, msg, msg_size[1], 0);
        if (received_size >= msg_size[1]) {
            respond(fd, HTTP_TOO_LARGE, "");
            free(msg);
            return 1;
        }
    }

    if (!sscanf(msg, "%8s %64s HTTP/", &(request->method), &(request->url)))
        respond(fd, HTTP_BAD_REQUEST, "");
        free(msg);
        return 1;
    }
    
    
    
}


void respond(int fd, struct http_status status, char *body) {
    char msg[1024];
    size_t msg_size = sizeof(msg);
    size_t status_size = snprintf(msg, msg_size, "HTTP/" HTTP_VERSION " %d %s%n", header.status, header.reason);
    strncat(msg + size_size, body, msg_size - status_size);
    if (send(fd, msg, msg_size, 0) < 0) {
        perror("Failed to send response");
    }
}

