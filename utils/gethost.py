import socket
from typing import Tuple, List, Dict


def get_host_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    print("本机ip为:", ip)
    return ip

class ServiceAddress:
    def __init__(self,host:str,port:int):
        self.host = host
        self.port = port
        self.count = 0

    def increment(self):
        self.count += 1


class LoadBalancer:
    def __init__(self, addresses:List[Dict[str, str|int]]=None):
        self.addresses : List[ServiceAddress] = []
        if addresses:
            self.init_addresses(addresses)

    def init_addresses(self, addresses: List[Dict[str, str | int]]):
        """初始化负载均衡器地址列表"""
        self.addresses.clear()
        for address in addresses:
            self.addresses.append(ServiceAddress(host = address['host'], port = address['port']))

    def get_address(self) -> Tuple[str|None, int|None]:
        if len(self.addresses) > 0:
            self.addresses.sort(key=lambda address: address.count)
            address = self.addresses[0]
            address.increment()
            return address.host, address.port
        else:
            raise ValueError("No addresses available in LoadBalancer")


def get_ip_port() -> Tuple[str, int]:
    sock_ip = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_ip.connect(('8.8.8.8', 80))
    ip = sock_ip.getsockname()[0]
    sock_ip.close()

    sock_port = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock_port.bind(("", 0))
    _, port = sock_port.getsockname()
    sock_port.close()
    return ip, port