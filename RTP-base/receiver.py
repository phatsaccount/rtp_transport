import argparse
import socket
import sys

from utils import *


def receiver(receiver_ip, receiver_port, window_size):

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((receiver_ip, receiver_port))

    connection = False
    expected_seq_num = 0
    window = {}

    while True:
        pks,ip = s.recvfrom(2048)

        pks_header = PacketHeader(pks[:16])
        data = pks[16:16 + pks_header.length]
        
        pks_checksum = pks_header.checksum
        pks_header.checksum = 0

        rev_checksum =  compute_checksum(pks_header / data)

        if pks_checksum != rev_checksum:
            continue

        if pks_header.type == START:
            if connection == False:
                connection = True
                expected_seq_num += 1
                window.clear()

                startAck_header = PacketHeader(ACK,pks_header.seq_num + 1,0,0)
                startAck_header.checksum = compute_checksum(startAck_header)
                startAck = bytes(startAck_header)
                s.sendto(startAck, ip)
            else:
                pass

        elif pks_header.type == END:
            if connection == True:
                connection = False

                endAck_header = PacketHeader(ACK, pks_header.seq_num + 1,0, 0)
                endAck_header.checksum  = compute_checksum(endAck_header)
                endAck = bytes(endAck_header)
                s.sendto(endAck, ip)
                break
            else:
                pass

        elif pks_header.type == DATA:
            if connection == True:
                if pks_header.seq_num >= expected_seq_num + window_size:
                    continue

                if pks_header.seq_num > expected_seq_num:
                    window[pks_header.seq_num] = data

                    ack_header = PacketHeader(type=ACK, seq_num=expected_seq_num, length=0)
                    ack_header.checksum = compute_checksum(ack_header)
                    s.sendto(bytes(ack_header), ip)

                elif pks_header.seq_num < expected_seq_num:
                    ack_header = PacketHeader(type=ACK, seq_num=expected_seq_num, length=0)
                    ack_header.checksum = compute_checksum(ack_header)
                    s.sendto(bytes(ack_header), ip)

                elif pks_header.seq_num == expected_seq_num:
                    sys.stdout.buffer.write(data)
                    sys.stdout.flush()

                    expected_seq_num += 1
                    if len(window) > 0:
                        while expected_seq_num in window:
                            sys.stdout.buffer.write(window[expected_seq_num])
                            del window[expected_seq_num]
                            expected_seq_num += 1
                    else:
                        pass

                    ack_header = PacketHeader(type=ACK, seq_num=expected_seq_num, length=0)
                    ack_header.checksum = compute_checksum(ack_header)
                    s.sendto(bytes(ack_header), ip)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "receiver_ip", help="The IP address of the host that receiver is running on"
    )
    parser.add_argument(
        "receiver_port", type=int, help="The port number on which receiver is listening"
    )
    parser.add_argument(
        "window_size", type=int, help="Maximum number of outstanding packets"
    )
    args = parser.parse_args()

    receiver(args.receiver_ip, args.receiver_port, args.window_size)


if __name__ == "__main__":
    main()
    