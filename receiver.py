from utils import *


class Receiver(Host):
    def __init__(self) -> None:
        super().__init__()
        self.logger = get_logger('arrival.log')
        self.buffer = [None for i in range(SEQ_NUM_SPACE)]

    def _open_file(self):
        self.file = open(self.file_name, 'w')

    def _on_receive(self, pkt: Packet):
        """Operations after recieve a packet pkt"""
        # Log into arrival.log
        if pkt.typ == 2:
            # EOT
            self.logger.info('EOT')
        else:
            self.logger.info(pkt.seqnum)
        if pkt.seqnum == (self.acked + 1) % SEQ_NUM_SPACE:
            # In-order packet
            if pkt.typ == 2:
                # EOT, ack EOT.
                self.eot_acked = True
                self._send(2, pkt.seqnum)
                return

            # Write data into output file.
            self.file.write(pkt.data)
            # Find the packets with larger seqnum in the buffer
            for i in range(pkt.seqnum+1, pkt.seqnum+MAX_WND_SIZE):
                if self.buffer[i % SEQ_NUM_SPACE]:
                    if self.buffer[i % SEQ_NUM_SPACE].typ == 2:
                        self.eot_acked = True
                        self._send(2, i % SEQ_NUM_SPACE)
                        break
                    # Write data from buffer and clear
                    self.file.write(self.buffer[i % SEQ_NUM_SPACE].data)
                    self.buffer[i % SEQ_NUM_SPACE] = None
                else:
                    # No more buffered packets
                    break
            # Update the largest seqnum and send ack.
            self._send(0, (i-1) % SEQ_NUM_SPACE)
            self.acked = (i-1) % SEQ_NUM_SPACE
        else:
            # Out-of-order
            if pkt.seqnum <= self.acked + 10 and (pkt.seqnum > self.acked or pkt.seqnum < self.acked -  (SEQ_NUM_SPACE-MAX_WND_SIZE-2)):
                # Seqnum is one of the next ten seqnum, store it in buffer.
                self.buffer[pkt.seqnum % SEQ_NUM_SPACE] = pkt
            self._send(0, (self.acked) % SEQ_NUM_SPACE) # Send duplicate ack


if __name__ == '__main__':
    if len(sys.argv) < 5:
        sys.stdout.write('Not enough argv\n')
    else:
        with Receiver() as receiver:
            receiver.receive()
