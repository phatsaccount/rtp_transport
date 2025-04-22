import argparse
import socket
import sys
import time

from utils import *


def sender(receiver_ip, receiver_port, window_size):
    TIME_OUT = 0.5
    MAX_PACKET = 1472
    window = {}
    seq_num = 0

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    s.settimeout(TIME_OUT)

    msg = sys.stdin.buffer.read()

    chunks = [msg[i : i + MAX_PACKET] for i in range(0, len(msg), MAX_PACKET)]

    start_pk = PacketHeader(START,seq_num, len(chunks), 0)

    start_pk.checksum = compute_checksum(start_pk)

    s.sendto(start_pk, (receiver_ip, receiver_port))
    window[seq_num] = start_pk
    seq_num += 1

    pk_nums = len(chunks)
    base = 0
    time_start = time.time()
    next_seq_num = 1
    

    while  base < pk_nums:
        time_now = time.time()

        #time out
        if time_now - time_start >= TIME_OUT:
            for pks in range(base,min(next_seq_num, base + window_size)):
                if pks in window:
                    s.sendto(window[pks], (receiver_ip, receiver_port))
                
            time_start = time_now
        while next_seq_num < base + window_size and next_seq_num < pk_nums:
            if next_seq_num < pk_nums - 1:
                #send data
                chunk_indx = next_seq_num - 1
                data_chunks = chunks[chunk_indx]

                pk_header = PacketHeader(DATA, next_seq_num, len(chunks), 0)
                pk_header.checksum = compute_checksum(pk_header / data_chunks)
                pk = bytes(pk_header / data_chunks)

                s.sendto(pk, (receiver_ip, receiver_port))

                window[next_seq_num] = pk
                next_seq_num += 1


            elif next_seq_num == pk_nums - 1:
                #send end

                end_header = PacketHeader(END, next_seq_num , 0, 0)
                end_header.checksum = compute_checksum(end_header)
                end_pk = bytes(end_header)
                window[next_seq_num] = end_pk
                next_seq_num += 1
                
                # end ack
                end_time = time.time()
                while time.time() - end_time < 0.5:
                    endAck_pk,_ = s.recvfrom(2048)
                    header_endAck_pk = PacketHeader(endAck_pk[:16])
                    if header_endAck_pk.type == END and header_endAck_pk.seq_num == pk_nums:
                        base = pk_nums
                        s.close()

        # data ack
        ack_pk,_ = s.recvfrom(2048)
        header_ack_pk = PacketHeader(ack_pk[:16])
        if header_ack_pk.type == ACK:
            if header_ack_pk.seq_num > base:
                for inx in range(base, header_ack_pk.seq_num):
                    if inx in window:
                        del window[inx]
                base = header_ack_pk.seq_num
                time_start = time.time()

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
