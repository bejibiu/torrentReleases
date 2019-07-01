import gzip
import urllib.parse
import urllib.request

import socks
from sockshandler import SocksiPyHandler

from settings import CONNECTION_ATTEMPTS, SOCKS5_IP, SOCKS5_PORT


def load_rutor_content(URL, attempts=CONNECTION_ATTEMPTS, useProxy=False):
    headers = {"Accept-encoding": "gzip",
               "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0"}

    return load_url_content(URL, headers=headers, attempts=attempts, useProxy=useProxy)


def load_url_content(url, headers=None, attempts=CONNECTION_ATTEMPTS, useProxy=False):
    if headers is None:
        headers = {}
    if useProxy and SOCKS5_IP:
        proxy_handler = SocksiPyHandler(socks.PROXY_TYPE_SOCKS5, SOCKS5_IP, SOCKS5_PORT)
        opener = urllib.request.build_opener(proxy_handler)
    else:
        opener = urllib.request.build_opener()

    request = urllib.request.Request(url, headers=headers)
    response = None
    n = attempts
    while n > 0:
        try:
            response = opener.open(request)
            break
        except:
            n = n - 1
            if n <= 0:
                raise ConnectionError("Ошибка соединения. Все попытки соединения израсходованы.")

    if response.info().get("Content-Encoding") == "gzip":
        gzip_file = gzip.GzipFile(fileobj=response)
        content = gzip_file.read().decode("utf-8")
    else:
        content = response.read().decode("utf-8")

    return content
