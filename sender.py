from threading import Lock, Thread

from utils import *


class Sender(Host):

    def __init__(self) -> None:
        super().__init__()
        self.timer = Timer(sys.argv[4])
        self.seq_logger = get_logger('seqnum.log')
        self.ack_logger = get_logger('ack.log')
        self.n_logger = get_logger('N.log')
        self.cwnd = 1
        self.sequence = 0
        self.duplicate_acks = 0
        self.event_num = 0
        self.mutex = Lock()
        self.log(self.n_logger, self.cwnd)

    def de_mod_acked(self):
        """Given mod 32 acked number and un-mod sequence number, return the un-mod acked number."""
        seqnum = self.acked + 1 + \
            (SEQ_NUM_SPACE * (self.sequence//SEQ_NUM_SPACE))
        if seqnum > self.sequence:
            seqnum -= SEQ_NUM_SPACE
        return seqnum

    def log(self, logger, msg: str, is_event=True):
        if is_event:
            # Log and incrememnt the event number.
            self.mutex.acquire()
            logger.info('t={} {}'.format(self.event_num, msg))
            self.event_num += 1
            self.mutex.release()
        else:
            logger.info('t={} {}'.format(self.event_num, msg))

    def _open_file(self):
        self.file = open(self.file_name, 'r')
        self.messages = list(self.file)

    def _send_data(self, seqnum=-1):
        """Send messages to receiver."""
        if seqnum == -1:
            # Use and increment default sequence number if arg not passed.
            seqnum = self.sequence
            self.sequence += 1
        if seqnum == len(self.messages):
            # Send EOT.
            self.sequence += 1
            self._send(2, seqnum % SEQ_NUM_SPACE)
            self.log(self.seq_logger, 'EOT')
        elif seqnum < len(self.messages):
            self.log(self.seq_logger, seqnum % 32)
            self._send(1, seqnum % SEQ_NUM_SPACE, self.messages[seqnum])
        if not self.timer.running:
            self.timer.begin()

    def _retransmit(self):
        """Re-transmit non-acked packet, used by fast re-transmit and timeout."""
        self.mutex.acquire()
        self.event_num += 1
        self.duplicate_acks = 0
        self.cwnd = 1
        self.log(self.n_logger, self.cwnd, False)
        self.mutex.release()
        self._send_data(self.de_mod_acked())
        self.timer.begin()

    def _on_receive(self, pkt: Packet):
        """Operations after recieving ACK."""
        # Log
        if pkt.typ == 2:
            # EOT
            self.log(self.ack_logger, 'EOT')
            self.eot_acked = True
            self.timer.begin()
            return
        self.log(self.ack_logger, pkt.seqnum)
        if self.acked == pkt.seqnum:
            # Duplicate ACK
            self.mutex.acquire()
            self.duplicate_acks += 1
            self.mutex.release()
            if self.duplicate_acks >= 3:
                # Fast re-transmit
                self._retransmit()
        elif pkt.seqnum > self.acked or self.acked > pkt.seqnum + (SEQ_NUM_SPACE-MAX_WND_SIZE-2):
            # New ACK
            if self.cwnd < MAX_WND_SIZE:
                # Increment window size.
                self.cwnd += 1
                self.log(self.n_logger, self.cwnd, False)
            self.acked = pkt.seqnum
            self.timer.begin() # Re-start timer.

    def send_messages(self):
        """Sending message with UDP"""
        while not self.eot_acked:
            if self.timer.timeout():
                self._retransmit()
            elif self.sequence <= len(self.messages) and self.sequence - 1 - self.de_mod_acked() < self.cwnd:
                # If sending window is not full
                self._send_data()


if __name__ == '__main__':
    if len(sys.argv) < 6:
        sys.stdout.write('Not enough argv\n')
    else:
        with Sender() as sender:
            send = Thread(target=sender.send_messages)
            rec = Thread(target=sender.receive)
            send.start()
            rec.start()
            send.join()
            rec.join()
