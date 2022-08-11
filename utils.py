import sys
import logging
import time
from socket import *

from packet import Packet


SEQ_NUM_SPACE = 32  # Sequence number space 0-31
MAX_WND_SIZE = 10  # Maximum sending window size


class Host():

    def __init__(self) -> None:
        self.host = gethostbyname(sys.argv[1])
        self.target_port, self.port = map(int, sys.argv[2:4])
        self.file_name = sys.argv[-1]
        self.eot_acked = False
        self.acked = -1

    def __enter__(self):
        self._open_file()
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.bind(('', int(self.port)))
        return self

    def __exit__(self, type, value, traceback):
        self.socket.close()
        self.file.close()

    def _open_file(self):
        pass

    def receive(self):
        while not self.eot_acked:
            message = self.socket.recvfrom(2048)[0]
            pkt = Packet(message)
            self._on_receive(pkt)

    def _send(self, pkt_type=0, seq=0, msg=''):
        pkt = Packet(pkt_type, seq, len(msg), msg)
        self.socket.sendto(pkt.encode(), (self.host, self.target_port))


def get_logger(file_name: str):
    """Given a file name and return a logger to that file."""
    logging.basicConfig(filemode='w')
    logger = logging.getLogger(file_name)
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.FileHandler(file_name, mode='w'))
    return logger


class Timer:
    def __init__(self, limit=1000) -> None:
        self.running = False
        self.limit = float(limit)/1000

    def begin(self):
        self.running = True
        self.start = time.time()

    def timeout(self) -> bool:
        """Return True if the timer expairs, return False otherwise."""
        if self.running and (time.time() - self.start > self.limit):
            return True
        return False
