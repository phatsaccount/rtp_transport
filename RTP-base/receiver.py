import argparse
import socket
import sys

from utils import PacketHeader, compute_checksum


def receiver(receiver_ip, receiver_port, window_size):
    
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((receiver_ip, receiver_port))
    
    in_connection = False
    expected_seq_num = 0
    buffer = {}
    end_seq_num = None  # end seq_num

    while True:
        pkt, address = s.recvfrom(2048)
        pkt_header = PacketHeader(pkt[:16])
        msg = pkt[16:16 + pkt_header.length]

        pkt_checksum = pkt_header.checksum
        pkt_header.checksum = 0
        computed_checksum = compute_checksum(pkt_header / msg)
        if pkt_checksum != computed_checksum:
            continue

        if pkt_header.type == 0:  # START
            if not in_connection:
                in_connection = True
                expected_seq_num = 1
                buffer.clear()
                end_seq_num = None

                ack_header = PacketHeader(type=3, seq_num=1, length=0)
                ack_header.checksum = compute_checksum(ack_header)
                s.sendto(bytes(ack_header), address)

        elif pkt_header.type == 1:  # END
            if in_connection == True:
                end_seq_num = pkt_header.seq_num
                #
                ack_header = PacketHeader(type=3, seq_num=end_seq_num + 1, length=0)
                ack_header.checksum = compute_checksum(ack_header)
                s.sendto(bytes(ack_header), address)

        elif pkt_header.type == 2:  # DATA
            if in_connection == True:
                if pkt_header.seq_num >= expected_seq_num + window_size:
                    continue

                if pkt_header.seq_num == expected_seq_num:
                    sys.stdout.buffer.write(msg)
                    sys.stdout.flush()
                    expected_seq_num += 1
                    while expected_seq_num in buffer:
                        sys.stdout.buffer.write(buffer[expected_seq_num])
                        sys.stdout.flush()
                        del buffer[expected_seq_num]
                        expected_seq_num += 1
                    ack_header = PacketHeader(type=3, seq_num=expected_seq_num, length=0)
                    ack_header.checksum = compute_checksum(ack_header)
                    s.sendto(bytes(ack_header), address)
                    
                elif pkt_header.seq_num > expected_seq_num:
                    buffer[pkt_header.seq_num] = msg
                    ack_header = PacketHeader(type=3, seq_num=expected_seq_num, length=0)
                    ack_header.checksum = compute_checksum(ack_header)
                    s.sendto(bytes(ack_header), address)
                else:
                    ack_header = PacketHeader(type=3, seq_num=expected_seq_num, length=0)
                    ack_header.checksum = compute_checksum(ack_header)
                    s.sendto(bytes(ack_header), address)

        if end_seq_num is not None and expected_seq_num == end_seq_num:
            break

    for seq in sorted(buffer):
        sys.stdout.buffer.write(buffer[seq])
        sys.stdout.flush()


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