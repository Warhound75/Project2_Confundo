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
    # ... [rest of the ConfundoSocket class]

    def _construct_syn_packet(self):
        # Construct a SYN packet with appropriate header fields
        syn_flag = 0x02  # TCP flag for SYN is 0x02
        header = struct.pack('!IIBB', self.sequence_number, self.acknowledgment_number, self.connection_id, syn_flag)
        self.sequence_number = (self.sequence_number + 1) % 0xFFFF
        syn_packet = header + b''
        return syn_packet

    # ... [rest of the methods]

    def send(self, data):
        # Check if the state is ESTABLISHED before sending data
        if self.state != 'ESTABLISHED':
            raise ValueError("Connection not established")
        # Implement sending data with congestion control
        # ... [rest of the send method]

    def close(self):
        # Implement the connection closing procedure
        if self.state != 'ESTABLISHED':
            return  # Connection is not established
     

