import socket
import time
import struct
import sys
import random
import threading

# Define constants
MAX_PACKET_SIZE = 424
MTU_SIZE = 412
INITIAL_CWND = 412
INITIAL_SSTHRESH = 12000
INITIAL_SEQUENCE_NUMBER = 50000
RETRANSMISSION_TIMEOUT = 0.5

# Function to simulate packet drop or duplication based on a probability
def simulate_packet_loss(probability):
    return random.random() < probability

class ConfundoSocket:
    def __init__(self):
        # Initialize socket and other necessary attributes
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sequence_number = 0
        self.acknowledgment_number = 0
        self.connection_id = 0
        self.cwnd = INITIAL_CWND
        self.ssthresh = INITIAL_SSTHRESH
        self.timeout = RETRANSMISSION_TIMEOUT
        self.state = 'CLOSED'  # Added state attribute

    def connect(self, address):
        # Implement the 3-way handshake to establish a connection
        # Step 1: Send a SYN packet to initiate the connection
        syn_packet = self._construct_syn_packet()
        self.sock.sendto(syn_packet, address)

        # Step 2: Wait for a SYN-ACK packet from the server
        self.sock.settimeout(self.timeout)  # Set a timeout for the response
        try:
            syn_ack_packet, server_address = self.sock.recvfrom(MAX_PACKET_SIZE)
            # Parse and validate the received SYN-ACK packet
            if self._is_valid_syn_ack_packet(syn_ack_packet):
                self._handle_syn_ack(syn_ack_packet)
            else:
                # Handle the case when the received packet is invalid
                pass
        except socket.timeout:
            # Handle the case when the server does not respond
            pass
        finally:
            self.sock.settimeout(None)  # Reset the socket timeout

        # Step 3: Send an ACK packet to complete the handshake
        ack_packet = self._construct_ack_packet()
        self.sock.sendto(ack_packet, address)

        self.state = 'ESTABLISHED'

    def _construct_syn_packet(self):
        # Construct a SYN packet with appropriate header fields
        syn_flag = 1  # 1-bit flag indicating SYN
        header = struct.pack('!IIBH', self.sequence_number, self.acknowledgment_number, self.connection_id, syn_flag)
        self.sequence_number += 1
        syn_packet = header + b''
        return syn_packet

    def _is_valid_syn_ack_packet(self, packet):
        # Ensure the packet has the correct length
        if len(packet) != 12:  # The SYN-ACK packet should have a fixed length of 12 bytes
            return False

        # Unpack the received packet to extract header fields
        try:
            seq_num, ack_num, conn_id, flags = struct.unpack('!IIBH', packet)
        except struct.error:
            return False  # Failed to unpack the packet

        # Check the flags to ensure it's a valid SYN-ACK packet
        syn_flag = (flags & 1) == 1  # Check if the SYN flag is set
        ack_flag = (flags & 2) == 2  # Check if the ACK flag is set

        if syn_flag and ack_flag:
            return True
        else:
            return False

    def _handle_syn_ack(self, syn_ack_packet):
        # Handle the received SYN-ACK packet
        # Update internal attributes with the received values
        seq_num, ack_num, conn_id, flags = struct.unpack('!IIBH', syn_ack_packet)
        self.acknowledgment_number = seq_num + 1  # Acknowledgment number should be the received sequence number + 1
        self.connection_id = conn_id
        # Additional processing if needed

    def _construct_ack_packet(self):
        # Construct an ACK packet to acknowledge the SYN-ACK
        ack_flag = 2  # 1-bit flag indicating ACK
        header = struct.pack('!IIBH', self.sequence_number, self.acknowledgment_number, self.connection_id, ack_flag)
        ack_packet = header + b''
        return ack_packet

    def send(self, data):
        # Implement sending data with congestion control
        # Construct the packet with data and appropriate flags
        packet = self._construct_packet(data)

        # Send the packet using socket.sendto
        self.sock.sendto(packet, (self.remote_address, self.remote_port))

        # Update sequence number and move the data pointer
        self.sequence_number += len(data)

    def _construct_packet(self, data):
        header = struct.pack('!I I H B', self.sequence_number, self.acknowledgment_number, self.connection_id, 0x00)
        packet = header + data
        return packet

    def close(self):
        # Implement the connection closing procedure
        # Send a FIN packet and wait for acknowledgment
        self.send_fin()
        self.receive_ack()  # Wait for ACK

        # Wait for 2 seconds for incoming packet(s) with FIN flag (FIN-WAIT)
        start_time = time.time()
        while time.time() - start_time < 2:
            packet, _ = self.sock.recvfrom(MAX_PACKET_SIZE)
            self.handle_received_packet(packet)
            if self.is_fin_packet(packet):
                self.send_ack()  # Respond to incoming FIN with ACK
                break

        # Close the connection and socket
        self.sock.close()

    def handle_received_packet(self, packet):
        # Implement the handling of received packets, including checking flags and updating states
        seq_number, ack_number, conn_id, flags = struct.unpack('!IIBB', packet[:12])
        is_syn = flags & 0x02
        is_ack = flags & 0x01
        is_fin = flags & 0x04

        # Check the connection ID to ensure it matches the current connection
        if conn_id != self.connection_id:
            print("Received packet with incorrect connection ID. Dropping.")
            return

        if is_syn:
            # Handle SYN packet
            if not is_ack:
                # Send SYN-ACK
                self._send_syn_ack(server_address)
        elif is_ack:
            # Handle ACK packet
            if is_fin:
                # Connection termination
                self._handle_fin_ack()
            else:
                # Handle regular data acknowledgment
                self._handle_data_ack(ack_number)
        elif is_fin:
            # Handle FIN packet
            self._handle_fin(server_address)
        else:
            # Regular data packet
            self._handle_data(packet, ack_number)
            # Acknowledge the received data
            self._send_ack(server_address)
             # Regular data packet
        self._handle_data(packet, ack_number)
        # Acknowledge the received data
        self._send_ack(server_address)

    def handle_timeout(self):
        # Implement timeout handling and congestion window adjustment
        current_time = time.time()

        # Check for unacknowledged packets and retransmit them
        for packet in self.unacknowledged_packets:
            if current_time - packet['send_time'] >= self.timeout:
                self._retransmit_packet(packet)

        # Adjust congestion control parameters
        self.ssthresh = self.cwnd / 2
        self.cwnd = INITIAL_CWND
        # Adjust congestion control parameters
        self.ssthresh = self.cwnd / 2
        self.cwnd = INITIAL_CWND

        # Start timeout timer for retransmission
        self.start_timeout_timer()

    def _retransmit_packet(self, packet):
        # Implement retransmission logic for a single packet
        # Resend the specified packet
        data = packet['data']
        self.send(data)
        packet['send_time'] = time.time()


class ConfundoClient:
    def __init__(self, hostname, port, filename):
        self.confundo_socket = ConfundoSocket()
        self.hostname = hostname
        self.port = port
        self.filename = filename

    def send_file(self):
        try:
            self.confundo_socket.connect((self.hostname, self.port))
            with open(self.filename, 'rb') as file:
                data = file.read(MTU_SIZE)
                while data:
                    self.confundo_socket.send(data)
                    data = file.read(MTU_SIZE)
            self.confundo_socket.close()

        except Exception as e:
            print(f"Error: {e}")

    def start_timer(self):
        timer = threading.Timer(RETRANSMISSION_TIMEOUT, self.handle_timeout)
        timer.start()

    def handle_timeout(self):
        print("Timeout! Retransmitting...")
        self.confundo_socket.retransmit_last_packet()
        self.start_timer()

    def run(self):
        try:
            # Initialize the CongestionControl instance
            congestion_control = CongestionControl()

            # Send the file with timeout handling and congestion control
            while True:
                data = file.read(MTU_SIZE)
                if not data:
                    break

                # Simulate packet drop
                if not simulate_packet_loss(0.1):  # 10% chance of packet drop
                    confundo_socket.send(data, sequence_number)
                else:
                    print("DROP", sequence_number, 0, 3)  # Print DROP information for debugging

                # Simulate packet duplication
                if simulate_packet_loss(0.05):  # 5% chance of packet duplication
                    confundo_socket.send(data, sequence_number)
                    print("DUP", sequence_number, 0, 3)  # Print DUP information for debugging

                data = file.read(MTU_SIZE)
                sequence_number += len(data)

                # Update congestion window based on acknowledgments
                congestion_control.update_cwnd(sequence_number)

            # Gracefully close the connection
            confundo_socket.close()

        except Exception as e:
            print(f"Error: {e}")

# Create an instance of ConfundoClient and initiate the file transfer
client = ConfundoClient(hostname, port, filename)
client.send_file()


            
class CongestionControl:
    def __init__(self):
        self.cwnd = INITIAL_CWND
        self.ssthresh = INITIAL_SSTHRESH
        self.last_acked_seq = 0
        self.timeout_start_time = None

    def update_cwnd(self, acked_seq):
        if self.cwnd < self.ssthresh:
            # Slow start
            self.cwnd += MTU_SIZE
        else:
            # Congestion avoidance
            self.cwnd += MTU_SIZE * MTU_SIZE // self.cwnd

        # Update last acknowledged sequence number
        self.last_acked_seq = max(self.last_acked_seq, acked_seq)

    def handle_timeout(self):
        # Timeout occurred, halve the congestion window and set SS-THRESH
        self.ssthresh = self.cwnd // 2
        self.cwnd = MTU_SIZE

        # Retransmit data after the last acknowledged byte
        self.retransmit_data()

        # Reset the timer
        self.timeout_start_time = None
    def retransmit_data(self):
        # Implement the logic to retransmit data after the last acknowledged byte
        start_seq = self.last_acked_seq + 1
        end_seq = start_seq + self.cwnd - 1  # Retransmit up to the congestion window size

        # Retrieve the data to be retransmitted
        data_to_retransmit = self.get_data_to_retransmit(start_seq, end_seq)

        # Send the retransmitted data
        confundo_socket.send(data_to_retransmit)
    def get_data_to_retransmit(self, start_seq, end_seq):
        # Implement the logic to retrieve the data to be retransmitted
        # This might involve accessing a buffer or file to resend the necessary portion

        # Example:
        with open(filename, 'rb') as file:
            file.seek(start_seq)
            data_to_retransmit = file.read(end_seq - start_seq + 1)

        return data_to_retransmit

    def start_timeout_timer(self):
        self.timeout_start_time = time.time()

    def is_timeout_expired(self):
        if self.timeout_start_time is None:
            return False

        return time.time() - self.timeout_start_time >= RETRANSMISSION_TIMEOUT

confundo_socket = ConfundoSocket()
confundo_socket.connect((hostname, port))

# Send the file data to the server
with open(filename, 'rb') as file:
    data = file.read(MTU_SIZE)
    sequence_number = INITIAL_SEQUENCE_NUMBER

    while data:
        # Simulate packet drop
        if not simulate_packet_loss(0.1):  # 10% chance of packet drop
            confundo_socket.send(data, sequence_number)
        else:
            print("DROP", sequence_number, 0, 3)  # Print DROP information for debugging

        # Simulate packet duplication
        if simulate_packet_loss(0.05):  # 5% chance of packet duplication
            confundo_socket.send(data, sequence_number)
            print("DUP", sequence_number, 0, 3)  # Print DUP information for debugging

        data = file.read(MTU_SIZE)
        sequence_number += len(data)

# Gracefully close the connection
confundo_socket.close()




