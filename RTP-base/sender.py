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
    window = {}
    total_packets = len(chunks) + 2  # START + DATA + END
    timer_start = time.time()

    # Send START 
    start_header = PacketHeader(type=0, seq_num=0, length=0)
    start_header.checksum = compute_checksum(start_header)
    start_packet = bytes(start_header)
    s.sendto(start_packet, (receiver_ip, receiver_port))
    window[0] = start_packet
    next_seq_num = 1

    while base < total_packets:
        current_time = time.time()
        # Retransmit
        if current_time - timer_start >= 0.5:
            for seq_num in range(base, min(next_seq_num, base + window_size)):
                if seq_num in window:
                    s.sendto(window[seq_num], (receiver_ip, receiver_port))
            timer_start = current_time

        # Send new packets 
        while next_seq_num < base + window_size and next_seq_num < total_packets:
            if next_seq_num == total_packets - 1:
                # Send END 
                end_header = PacketHeader(type=1, seq_num=next_seq_num, length=0)
                end_header.checksum = compute_checksum(end_header)
                end_packet = bytes(end_header)
                s.sendto(end_packet, (receiver_ip, receiver_port))
                window[next_seq_num] = end_packet
                next_seq_num += 1
            else:
                # Send DATA
                chunk_idx = next_seq_num - 1
                data_chunk = chunks[chunk_idx]
                data_header = PacketHeader(type=2, seq_num=next_seq_num, length=len(data_chunk))
                data_header.checksum = compute_checksum(data_header / data_chunk)
                data_packet = bytes(data_header / data_chunk)
                s.sendto(data_packet, (receiver_ip, receiver_port))
                window[next_seq_num] = data_packet
                next_seq_num += 1

        # ACKs
        try:
            ack_pkt, _ = s.recvfrom(2048)
            ack_header = PacketHeader(ack_pkt[:16])
            if ack_header.type == 3 and ack_header.seq_num > base:
                for seq_num in range(base, ack_header.seq_num):
                    if seq_num in window:
                        del window[seq_num]
                base = ack_header.seq_num
                timer_start = time.time()
        except socket.timeout:
            pass
        except ConnectionResetError:
            pass

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