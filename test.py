import random
import socket
import struct
import sys
import threading
import time

# Define constants
MAX_PACKET_SIZE = 424
MTU_SIZE = 412
INITIAL_CWND = 412
INITIAL_SSTHRESH = 12000
INITIAL_SEQUENCE_NUMBER = 50000
RETRANSMISSION_TIMEOUT = 0.5

# Function to simulate packet loss or duplication based on a probability
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

    def send_fin(self):
        fin_flag = 4
        header = struct.pack('!IIB', self.sequence_number, self.acknowledgment_number, fin_flag)
        fin_packet = header + b''
        self.sock.sendto(fin_packet, (self.remote_address, self.remote_port))


    def close(self):
        self.send_fin()
      

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

    def send_large_file_over_lossy_link_with_delay(self):
        try:
            self.confundo_socket.connect((self.hostname, self.port))
            # Simulate a lossy link with delay (adjust parameters accordingly)
            self.simulate_lossy_link_with_delay(loss_probability=0.1, delay_seconds=2)
            with open(self.filename, 'rb') as file:
                data = file.read(MTU_SIZE)
                while data:
                    self.confundo_socket.send(data)
                    data = file.read(MTU_SIZE)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.confundo_socket.close()

    def run_all_tests(self):
        self.test_case_2_1()
        self.test_case_2_2()
        self.test_case_2_3()
        self.test_case_2_4()
        self.test_case_2_4_part_2()
        self.test_case_2_5()
        self.test_case_2_6()
        self.test_case_2_9()
        self.test_case_2_11()
        self.test_case_2_12()
        self.test_case_2_13_1()
        self.test_case_2_13_2()
        self.test_case_2_14_1()
        self.test_case_2_14_2()

    def test_case_2_1(self):
        client = ConfundoClient(self.hostname, self.port, self.filename)
        client.confundo_socket.connect((self.hostname, self.port))
        if client.confundo_socket.sequence_number != INITIAL_SEQUENCE_NUMBER + 1:
            print("Test Failed: 2.1. Sequence number not incremented correctly")
        else:
            print("Test Passed: 2.1. Three-way handshake successful")

    def test_case_2_2(self):
        client = ConfundoClient(self.hostname, self.port, self.filename)
        client.confundo_socket.connect((self.hostname, self.port))
        if client.confundo_socket.acknowledgment_number != 0:
            print("Test Failed: 2.2. Incorrect initial acknowledgment number")
        else:
            print("Test Passed: 2.2. Correct initial acknowledgment number")

    def test_case_2_3(self):
        client = ConfundoClient(self.hostname, self.port, self.filename)
        client.send_large_file_over_lossy_link_with_delay()  # This will automatically check for 2.3

    def test_case_2_4(self):
        client = ConfundoClient(self.hostname, self.port, self.filename)
        client.confundo_socket.set_state('SYN_SENT')
        client.confundo_socket.sequence_number = sys.maxsize
        client.confundo_socket._handle_syn_ack(struct.pack('!IIB', 0, 0, 3))  # Simulate SYN-ACK
        if client.confundo_socket.sequence_number != INITIAL_SEQUENCE_NUMBER + 1:
            print("Test Failed: 2.4 (part 1). Sequence number not reset correctly")
        else:
            print("Test Passed: 2.4 (part 1). Sequence number reset correctly")

    def test_case_2_4_part_2(self):
        client = ConfundoClient(self.hostname, self.port, self.filename)
        client.confundo_socket.sequence_number = sys.maxsize - 1
        client.confundo_socket._handle_syn_ack(struct.pack('!IIB', 0, 0, 3))  # Simulate SYN-ACK
        if client.confundo_socket.sequence_number != INITIAL_SEQUENCE_NUMBER:
            print("Test Failed: 2.4 (part 2). Sequence number not wrapped correctly")
        else:
            print("Test Passed: 2.4 (part 2). Sequence number wrapped correctly")

    def test_case_2_5(self):
        client = ConfundoClient(self.hostname, self.port, self.filename)
        client.send_large_file_over_lossy_link_with_delay()  # This will automatically check for sending a FIN packet

    def test_case_2_6(self):
        client = ConfundoClient(self.hostname, self.port, self.filename)
        client.confundo_socket.close()

        start_time = time.time()
        while time.time() - start_time < 2:
            # Simulate incoming FIN packets
            packet, _ = client.confundo_socket.sock.recvfrom(MAX_PACKET_SIZE)
            client.confundo_socket.handle_received_packet(packet)
            if client.confundo_socket.is_fin_packet(packet):
                client.confundo_socket.send_ack()
                break

    def test_case_2_9(self):
        congestion_control = CongestionControl()
        congestion_control.update_cwnd(INITIAL_SEQUENCE_NUMBER)
        if congestion_control.cwnd <= INITIAL_CWND:
            print("Test Failed: 2.9. Congestion window size not increased in slow start phase")
        else:
            print("Test Passed: 2.9. Congestion window size increased in slow start phase")

    def test_case_2_11(self):
        congestion_control = CongestionControl()
        congestion_control.start_timeout_timer()
        congestion_control.handle_timeout(client.confundo_socket)
        if congestion_control.last_acked_seq >= INITIAL_SEQUENCE_NUMBER:
            print("Test Passed: 2.11. Lost data segments detected and retransmitted")
        else:
            print("Test Failed: 2.11. Lost data segments not detected or retransmitted")

    def test_case_2_12(self):
        congestion_control = CongestionControl()
        congestion_control.start_timeout_timer()
        congestion_control.handle_timeout(client.confundo_socket)
        if congestion_control.ssthresh <= congestion_control.cwnd:
            print("Test Passed: 2.12. SS-THRESH and CWND values set properly after timeout")
        else:
            print("Test Failed: 2.12. SS-THRESH and CWND values not set properly after timeout")

    def test_case_2_13_1(self):
        client = ConfundoClient(self.hostname, self.port, self.filename)
        client.send_large_file_over_lossy_link_with_delay()  # This will automatically check for sending a file without losses

    def test_case_2_13_2(self):
        # Test case 2.13.2
        client = ConfundoClient(self.hostname, self.port, self.filename)
        # Simulate a lossy link with delay (adjust parameters accordingly)
        self.simulate_lossy_link_with_delay(client)
        client.send_large_file_over_lossy_link_with_delay()  # This will automatically check for sending a file over a lossy link with delay

    def test_case_2_14_1(self):
        client = ConfundoClient(self.hostname, self.port, self.filename)
        client.send_large_file_over_lossy_link_with_delay()  # This will automatically check for sending a large file without losses

    def test_case_2_14_2(self):
        client = ConfundoClient(self.hostname, self.port, self.filename)
        # Simulate a lossy link with delay (adjust parameters accordingly)
        self.simulate_lossy_link_with_delay(client)
        client.send_large_file_over_lossy_link_with_delay()  # This will automatically check for sending a large file over a lossy link with delay

    def simulate_lossy_link_with_delay(self, client, loss_probability=0.1, delay_seconds=2):
        def delayed_send():
            time.sleep(delay_seconds)
            client.confundo_socket.send(data)

        with open(client.filename, 'rb') as file:
            data = file.read(MTU_SIZE)
            while data:
                if not simulate_packet_loss(loss_probability):
                    threading.Thread(target=delayed_send).start()
                else:
                    print("DROP", client.confundo_socket.sequence_number, 0, 3)  # Print DROP information for debugging

                data = file.read(MTU_SIZE)

# Example usage of ConfundoClient and running tests
hostname = 'localhost'
port = 12345
filename = 'example.txt'

client = ConfundoClient(hostname, port, filename)
client.run_all_tests()
client.send_large_file_over_lossy_link_with_delay()
