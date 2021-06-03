'''
This file contains basic utility functions that you can use.
'''
import binascii

MAX_NUM_CLIENTS = 10
TIME_OUT = 0.5 # 500ms
NUM_OF_RETRANSMISSIONS = 3
CHUNK_SIZE = 1400 # 1400 Bytes

def validate_checksum(message):
    '''
    Validates Checksum of a message and returns true/false
    '''
    try:
        msg, checksum = message.rsplit('|', 1)
        msg += '|'
        return generate_checksum(msg.encode()) == checksum
    except BaseException:
        return False


def generate_checksum(message):
    '''
    Returns Checksum of the given message
    '''
    return str(binascii.crc32(message) & 0xffffffff)


def make_packet(msg_type="data", seqno=0, msg=""):
    '''
    This will add the header to your message.
    The formats is `<message_type> <sequence_number> <body> <checksum>`
    msg_type can be data, ack, end, start
    seqno is a packet sequence number (integer)
    msg is the actual message string
    '''
    body = "%s|%d|%s|" % (msg_type, seqno, msg)
    checksum = generate_checksum(body.encode())
    packet = "%s%s" % (body, checksum)
    return packet


def parse_packet(message):
    '''
    This function will parse the packet in the same way it was made in the above function.
    '''
    pieces = message.split('|')
    msg_type, seqno = pieces[0:2]
    checksum = pieces[-1]
    data = '|'.join(pieces[2:-1])
    return msg_type, seqno, data, checksum


def make_message(msg_type, msg_format, message=None):
    '''
    This function can be used to format your message according
    to any one of the formats described in the documentation.
    msg_type defines type like join, disconnect etc.
    msg_format is either 1,2,3 or 4
    msg is remaining. 
    '''
    if msg_format == 2:
        msg_len = 0
        return "%s %d" % (msg_type, msg_len)
        # return "%s:" % (msg_type)
    if msg_format in [1, 3, 4]:
        msg_len = len(message)
        return "%s %d %s" % (msg_type, msg_len, message)
        # return "%s %s" % (msg_type, message)
    return ""

def final_msg(msg_type, msg_format, msg, packet_type="data", seq=0): # makes a final message to send to server
    msg_1 = make_message(msg_type, msg_format, msg)
    msg_2 = make_packet(packet_type, int(seq), msg_1)
    return msg_2

def get_name(msg): # extracts username
    msg_list = msg.split()
    name = "".join(msg_list[-1])
    return name

def key_from_value(dic, add): #extracts key from a given value
    keys_list = list(dic.keys())
    values_list = list(dic.values())
    position = values_list.index(add)
    name = keys_list[position]
    return name
        
