#pragma once 

#include <sys/socket.h>


#define HTTP_VERSION "1.1"

#define HTTP_GET "GET"
#define HTTP_HED "HEAD"
#define HTTP_PST "POST"
#define HTTP_PUT "PUT"   
#define HTTP_DEL "DELETE"
#define HTTP_CON "CONNECT"
#define HTTP_OPT "OPTIONS"
#define HTTP_TRC "TRACE"
#define HTTP_PCH "PATCH"


void server_init(void);


void server_run(void);


struct http_status {
    int code;
    char reason[32];
};


#define HTTP_OK {200, "OK"}
#define HTTP_BAD_REQUEST {400, "Bad Request"}
#define HTTP_NOT_FOUND {404, "Not Found"}
#define HTTP_NOT_ALLOWED {405, "Method Not Allowed"}
#define HTTP_TOO_LARGE {413, "Content Too Large"}


struct http_request {
    char method[8];
    char url[64];
};


