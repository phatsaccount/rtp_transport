import argparse
import socket
import sys
import time

from utils import PacketHeader, compute_checksum


def sender(receiver_ip, receiver_port, window_size):
    
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0.01)

    message = sys.stdin.buffer.read()
    max_payload_size = 1456
    chunks = [message[i:i+max_payload_size] for i in range(0, len(message), max_payload_size)]

    base = 0
    next_seq_num = 0
    total_packets = len(chunks) + 2  # START + DATA + END

    window = {}
    acked = {}

    timer_start = time.time()

    # Prepare all packets
    packets = {}

    # START packet
    start_header = PacketHeader(type=0, seq_num=0, length=0)
    start_header.checksum = compute_checksum(start_header)
    packets[0] = bytes(start_header)

    # DATA packets
    for i, chunk in enumerate(chunks):
        seq = i + 1
        data_header = PacketHeader(type=2, seq_num=seq, length=len(chunk))
        data_header.checksum = compute_checksum(data_header / chunk)
        packets[seq] = bytes(data_header / chunk)
    # END packet
    end_seq = len(chunks) + 1
    end_header = PacketHeader(type=1, seq_num=end_seq, length=0)
    end_header.checksum = compute_checksum(end_header)
    packets[end_seq] = bytes(end_header)

    for seq in range(total_packets):
        acked[seq] = False

    while base < total_packets:
        # Send new packets in window
        while next_seq_num < base + window_size and next_seq_num < total_packets:
            if next_seq_num not in window:
                s.sendto(packets[next_seq_num], (receiver_ip, receiver_port))
                window[next_seq_num] = packets[next_seq_num]
            next_seq_num += 1

        # ACK
        try:
            while True:
                ack_pkt, _ = s.recvfrom(2048)
                ack_header = PacketHeader(ack_pkt[:16])

                if ack_header.type == 3 and base <= ack_header.seq_num < base + window_size:
                    acked[ack_header.seq_num] = True
        except socket.timeout:
            pass
        except ConnectionResetError:
            pass

        # Retransmit
        if time.time() - timer_start >= 0.5:
            for seq_num in range(base, min(base + window_size, total_packets)):
                if not acked[seq_num] and seq_num in window:
                    s.sendto(window[seq_num], (receiver_ip, receiver_port))
            timer_start = time.time()

        # Slide window forward
        while base < total_packets and acked[base]:
            if base in window:
                del window[base]
            base += 1

    s.close()


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

    sender(args.receiver_ip, args.receiver_port, args.window_size)


if __name__ == "__main__":
    main()