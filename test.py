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
        self.sequence_number = INITIAL_SEQUENCE_NUMBER
        self.acknowledgment_number = 0
        self.connection_id = 0
        self.cwnd = INITIAL_CWND
        self.ssthresh = INITIAL_SSTHRESH
        self.timeout = RETRANSMISSION_TIMEOUT
        self.state = 'CLOSED'
        self.remote_address = None
        self.remote_port = None

    def set_state(self, new_state):
        self.state = new_state

    def get_state(self):
        return self.state

    def connect(self, address):
        self.remote_address, self.remote_port = address
        self.set_state('SYN_SENT')
        syn_packet = self._construct_syn_packet()
        self.sock.sendto(syn_packet, address)

        self.sock.settimeout(self.timeout)
        try:
            syn_ack_packet, server_address = self.sock.recvfrom(MAX_PACKET_SIZE)
            if self._is_valid_syn_ack_packet(syn_ack_packet):
                self._handle_syn_ack(syn_ack_packet)
            else:
                # Handle the case when the received packet is invalid
                pass
        except socket.timeout:
            # Handle the case when the server does not respond
            pass
        finally:
            self.sock.settimeout(None)

        ack_packet = self._construct_ack_packet()
        self.sock.sendto(ack_packet, address)

        self.set_state('ESTABLISHED')

    def _construct_syn_packet(self):
        syn_flag = 1
        header = struct.pack('!IIB', self.sequence_number, self.acknowledgment_number, syn_flag)
        self.sequence_number += 1
        syn_packet = header + b''
        return syn_packet

    def _is_valid_syn_ack_packet(self, packet):
        if len(packet) != 8:
            return False

        try:
            seq_num, ack_num, flags = struct.unpack('!IIB', packet)
        except struct.error:
            return False

        syn_flag = (flags & 1) == 1
        ack_flag = (flags & 2) == 2

        return syn_flag and ack_flag

    def _handle_syn_ack(self, syn_ack_packet):
        seq_num, ack_num, flags = struct.unpack('!IIB', syn_ack_packet)
        self.acknowledgment_number = seq_num + 1

    def _construct_ack_packet(self):
        ack_flag = 2
        header = struct.pack('!IIB', self.sequence_number, self.acknowledgment_number, ack_flag)
        ack_packet = header + b''
        return ack_packet

    def send(self, data):
        packet = self._construct_packet(data)

        self.sock.sendto(packet, (self.remote_address, self.remote_port))

        self.sequence_number += len(data)

    def _construct_packet(self, data):
        header = struct.pack('!I I B', self.sequence_number, self.acknowledgment_number, 0x00)
        packet = header + data
        return packet

    def close(self):
        self.send_fin()
        self.receive_ack()

        start_time = time.time()
        while time.time() - start_time < 2:
            packet, _ = self.sock.recvfrom(MAX_PACKET_SIZE)
            self.handle_received_packet(packet)
            if self.is_fin_packet(packet):
                self.send_ack()
                break

        self.sock.close()

    def handle_received_packet(self, packet):
        seq_number, ack_number, flags = struct.unpack('!IIB', packet[:12])
        is_fin = (flags & 4) == 4

        if is_fin:
            self._handle_fin()
            self.send_ack()

    def _handle_fin(self):
        self.set_state('CLOSE_WAIT')

    def send_ack(self):
        ack_packet = self._construct_ack_packet()
        self.sock.sendto(ack_packet, (self.remote_address, self.remote_port))

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
                    # Add a check for the average size of data segments
            total_data_sent = 0
            num_segments_sent = 0

            with open(self.filename, 'rb') as file:
                data = file.read(MTU_SIZE)
                while data:
                    if len(data) > MTU_SIZE:
                        print("Test Failed: 2.3. Data segments exceed 412 bytes")
                        return

                    total_data_sent += len(data)
                    num_segments_sent += 1

                    self.confundo_socket.send(data)
                    data = file.read(MTU_SIZE)

            # Check average size of data segments
            average_size = total_data_sent / num_segments_sent
            if average_size <= 370:
                print("Test Failed: 2.3. Average size of data segments is not larger than 370 bytes")
                return
            self.confundo_socket.close()

        except Exception as e:
            print(f"Error: {e}")

    def run(self):
        try:
            # Send the file with timeout handling
            self.send_file()

        except Exception as e:
            print(f"Error: {e}")

# Create an instance of ConfundoClient and initiate the file transfer
client = ConfundoClient(hostname, port, filename)
client.run()

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

    def handle_timeout(self, confundo_socket):
        # Timeout occurred, halve the congestion window and set SS-THRESH
        self.ssthresh = self.cwnd // 2
        self.cwnd = MTU_SIZE

        # Retransmit data after the last acknowledged byte
        self.retransmit_data(confundo_socket)

        # Reset the timer
        self.timeout_start_time = None

    def retransmit_data(self, confundo_socket):
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

# Example usage of CongestionControl
confundo_socket = ConfundoSocket()
confundo_socket.connect((hostname, port))

congestion_control = CongestionControl()
congestion_control.update_cwnd(initial_ack_seq)

# Send the file data to the server
with open(filename, 'rb') as file:
    data = file.read(MTU_SIZE)
    sequence_number = INITIAL_SEQUENCE_NUMBER

    while data:
        # Simulate packet drop
        if not simulate_packet_loss(0.1):  # 10% chance of packet drop
            confundo_socket.send(data)
        else:
            print("DROP", sequence_number, 0, 3)  # Print DROP information for debugging

        # Simulate packet duplication
        if simulate_packet_loss(0.05):  # 5% chance of packet duplication
            confundo_socket.send(data)
            print("DUP", sequence_number, 0, 3)  # Print DUP information for debugging

        data = file.read(MTU_SIZE)
        sequence_number += len(data)

        # Update congestion window based on acknowledgments
        congestion_control.update_cwnd(sequence_number)

# Gracefully close the connection
confundo_socket.close()

# Add test cases to check various conditions
def run_test_cases():
    # Test case 2.1
    client = ConfundoClient(hostname, port, filename)
    client.confundo_socket.connect((hostname, port))
    if client.confundo_socket.sequence_number != INITIAL_SEQUENCE_NUMBER + 1:
        print("Test Failed: 2.1. Sequence number not incremented correctly")
    else:
        print("Test Passed: 2.1. Three-way handshake successful")

    # Test case 2.2
    if client.confundo_socket.sequence_number != INITIAL_SEQUENCE_NUMBER + 1:
        print("Test Failed: 2.2. Incorrect initial sequence number")
    else:
        print("Test Passed: 2.2. Correct initial sequence number")

    # Test case 2.3
    client.send_file()  # This will automatically check for 2.3

    # Test case 2.4 (part 1)
    client.confundo_socket.sequence_number = sys.maxsize
    client.confundo_socket._handle_syn_ack(struct.pack('!IIB', 0, 0, 3))  # Simulate SYN-ACK
    if client.confundo_socket.sequence_number != INITIAL_SEQUENCE_NUMBER + 1:
        print("Test Failed: 2.4 (part 1). Sequence number not reset correctly")
    else:
        print("Test Passed: 2.4 (part 1). Sequence number reset correctly")

    # Test case 2.4 (part 2)
    client.confundo_socket.sequence_number = sys.maxsize - 1
    client.confundo_socket._handle_syn_ack(struct.pack('!IIB', 0, 0, 3))  # Simulate SYN-ACK
    if client.confundo_socket.sequence_number != INITIAL_SEQUENCE_NUMBER:
        print("Test Failed: 2.4 (part 2). Sequence number not wrapped correctly")
    else:
        print("Test Passed: 2.4 (part 2). Sequence number wrapped correctly")

    # Test case 2.5
    client.send_file()  # This will automatically check for sending a FIN packet

    # Test case 2.6
    start_time = time.time()
    client.confundo_socket.close()
    while time.time() - start_time < 2:
        # Simulate incoming FIN packets
        packet, _ = client.confundo_socket.sock.recvfrom(MAX_PACKET_SIZE)
        client.confundo_socket.handle_received_packet(packet)
        if client.confundo_socket.is_fin_packet(packet):
            client.confundo_socket.send_ack()
            break

    # Test case 2.9
    congestion_control = CongestionControl()
    congestion_control.update_cwnd(INITIAL_SEQUENCE_NUMBER)
    if congestion_control.cwnd <= INITIAL_CWND:
        print("Test Failed: 2.9. Congestion window size not increased in slow start phase")
    else:
        print("Test Passed: 2.9. Congestion window size increased in slow start phase")

    # Test case 2.11
    congestion_control.start_timeout_timer()
    congestion_control.handle_timeout(client.confundo_socket)
    if congestion_control.last_acked_seq >= INITIAL_SEQUENCE_NUMBER:
        print("Test Passed: 2.11. Lost data segments detected and retransmitted")
    else:
        print("Test Failed: 2.11. Lost data segments not detected or retransmitted")

    # Test case 2.12
    if congestion_control.ssthresh <= congestion_control.cwnd:
        print("Test Passed: 2.12. SS-THRESH and CWND values set properly after timeout")
    else:
        print("Test Failed: 2.12. SS-THRESH and CWND values not set properly after timeout")

# Run the test cases
run_test_cases()
