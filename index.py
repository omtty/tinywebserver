#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import socket
from urllib.parse import urlparse
import os


class TinyWebException(BaseException):
    pass


def recv(socket, count):
    if count > 0:
        recv_buffer = socket.recv(count)
        if recv_buffer == b"":
            raise TinyWebException("socket.rect调用失败！")
        return recv_buffer
    return b""


def read_line(socket):
    recv_buffer = b''
    while True:
        recv_buffer += recv(socket, 1)
        if recv_buffer.endswith(b"\r\n"):
            break
    return recv_buffer


def read_request_line(socket):
    """
    读取http请求行
    """
    # 读取行并把\r\n替换成空字符，最后以空格分离
    values = read_line(socket).replace(b"\r\n", b"").split(b" ")
    return dict({
        # 请求方法
        b'method': values[0],
        # 请求路径
        b'path': values[1],
        # 协议版本
        b'protocol': values[2]
    })


def bytesToInt(bs):
    """
    把bytes转化为int
    """
    return int(bs.decode(encoding="utf-8"))


def read_request_headers(socket):
    """
    读取http请求头
    """
    headers = dict()
    line = read_line(socket)
    while line != b"\r\n":
        keyValuePair = line.replace(b"\r\n", b"").split(b": ")
        # 统一header中的可以为小写，方便后面使用
        keyValuePair[0] = keyValuePair[0].decode(
            encoding="utf-8").lower().encode("utf-8")
        if keyValuePair[0] == b"content-length":
            # 如果是cotent-length我们需要把结果转化为整数，方便后面读取body
            headers[keyValuePair[0]] = bytesToInt(keyValuePair[1])
        else:
            headers[keyValuePair[0]] = keyValuePair[1]
        line = read_line(socket)
    # 如果heander中没有content-length，我们就手动把cotent-length设置为0
    if not headers.__contains__(b"content-length"):
        headers[b"content-length"] = 0
    return headers


def read_request_body(socket, content_length):
    """
    读取http请求体
    """
    return recv(socket, content_length)


def send_response():
    print("send response")


def static_type(path):
    if path.endswith(".html"):
        return b"text/html; charset=UTF-8"
    elif path.endswith(".png"):
        return b"image/png; charset=UTF-8"
    elif path.endswith(".jpg"):
        return b"image/jpg; charset=UTF-8"
    elif path.endswith(".jpeg"):
        return b"image/jpeg; charset=UTF-8"
    elif path.endswith(".gif"):
        return b"image/gif; charset=UTF-8"
    elif path.endswith(".js"):
        return b"application/javascript; charset=UTF-8"
    elif path.endswith(".css"):
        return b"text/css; charset=UTF-8"
    else:
        return b"text/plain; charset=UTF-8"


def serve_static(socket, path):
    # 检查是否有path读的权限和具体path对应的资源是否是文件
    if os.access(path, os.R_OK) and os.path.isfile(path):
        # 文件类型
        content_type = static_type(path)
        # 文件大小
        content_length = os.stat(path).st_size
        # 拼装Http响应
        response_headers = b"HTTP/1.0 200 OK\r\n"
        response_headers += b"Server: Tiny Web Server\r\n"
        response_headers += b"Connection: close\r\n"
        response_headers += b"Content-Type: " + content_type + b"\r\n"
        response_headers += b"Content-Length: %d\r\n" % content_length
        response_headers += b"\r\n"
        # 发送http响应头
        socket.send(response_headers)
        # 以二进制的方式读取文件
        with open(path, "rb") as f:
            # 发送http消息体
            socket.send(f.read())
    else:
        raise TinyWebException("没有访问权限")


def do_it(socket, request_line, request_headers, request_body):
    """
    处理http请求
    """

    # 生成静态资源的目标地址，在这里我们所有的静态文件都统一放在static目录下面
    parse_result = urlparse(request_line[b"path"])
    current_dir = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(current_dir, "static" +
                             parse_result.path.decode(encoding="utf-8"))
    
    # 如果静态资源存在就向客户端提供静态文件
    if os.path.exists(file_path):
        serve_static(socket, file_path)
    else:
        # 静态文件不存在，向客户展示404页面
        serve_static(socket, os.path.join(current_dir, "static/404.html"))


def handle_error(socket, error):
    print(error)
    error_message = str(error).encode("utf-8")
    response = b"HTTP/1.0 500 Server Internal Error\r\n"
    response += b"Server: Tiny Web Server\r\n"
    response += b"Connection: close\r\n"
    response += b"Content-Type: text/html; charset=UTF-8\r\n"
    response += b"Content-Length: %d\r\n" % len(error_message)
    response += b"\r\n"
    response += error_message
    socket.send(response)


def process_request(client, addr):
    try:
        # 获取请求行
        request_line = read_request_line(client)
        # 获取请求头
        request_headers = read_request_headers(client)
        # 获取请求体
        request_body = read_request_body(
            client, request_headers[b"content-length"])
        # 处理客户端请求
        do_it(client, request_line, request_headers, request_body)
    except BaseException as error:
        # 打印错误信息
        handle_error(client, error)
    finally:
        # 关闭客户端请求
        client.close()


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("127.0.0.1", 3000))
server.listen(5)

print("启动tiny web server，port = 3000")

while True:
    client, addr = server.accept()
    print("请求地址：%s" % str(addr))
    # 处理请求
    process_request(client, addr)
