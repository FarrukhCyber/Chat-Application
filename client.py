'''
This module defines the behaviour of a client in your Chat Application
'''
import sys
import getopt
import socket
import random
from threading import Thread
import os
import util
import time
from queue import Queue


'''
Write your code inside this class. 
In the start() function, you will read user-input and act accordingly.
receive_handler() function is running another thread and you have to listen 
for incoming messages in this function.
'''
# global variables
loop = True
ack_queue = Queue(maxsize= 0)
lost_pkt = []



class Client:
    '''
    This is the main Client Class. 
    '''
    def __init__(self, username, dest, port, window_size):
        self.server_addr = dest
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(None)
        self.sock.bind(('', random.randint(10000, 40000)))
        self.name = username
        self.window = window_size
        self.exit = False
        self.data_queue = Queue(0)


    def start(self):
        '''
        Main Loop is here
        Start by sending the server a JOIN message.
        Waits for userinput and then process it
        '''
        global loop
        global ack_queue

        self.send_response("join", 1, self.name)

            
        time.sleep(0.001)

        
        while loop:

            to_send = input()
            to_send_list = to_send.split()
            
            if to_send_list[0] == "list":
                self.send_response("request_users_list", 2, None)
  
                
            elif to_send_list[0] == "help":
                print("FORMATS:")
                print("Message: msg <number_of_users> <username1> <username2> ... <message>")
                print("Available Users: list")
                print("File Sharing: file <number_of_users> <username1> <username2> ... <file_name>")
                print("Quit: quit")
                
            elif to_send_list[0] == "quit":

                print("quitting")
                self.send_response("disconnect", 1, self.name)
                loop = False
                # return
                
            elif to_send_list[0] == "msg":

                del to_send_list[0]
                msg_1 = " ".join(to_send_list)
                
                self.send_response("send_message", 4, msg_1)
                
            elif to_send_list[0] == "file":
                
                file_name = to_send_list[-1]
                del to_send_list[0]
                message = " ".join(to_send_list)

                with open(file_name) as f:
                    lines = f.read().splitlines()
                    file_content = "\n".join(lines)
                    message = message + " " + file_content
                    
                self.send_response("send_file", 4, message)

            else:
                print("incorrect userinput format")

            
    def receive_handler(self):
        global loop
        global ack_queue
        seq_list = []
        seq_order = []

        while loop:
            
            msg, _= self.sock.recvfrom(4096)
            packet_type, seq, data, _ = util.parse_packet(msg.decode("utf-8"))
            seq = int(seq)

            # handling duplicate packets
            # if seq in seq_list:
            #     self.ack_sender(seq)
            #     continue
            
            # handling out of order packets
            # if (packet_type != "ack" and seq_order and seq_order[-1] != seq):
            #     continue
            
                        
            if packet_type == "ack":
                ack_queue.put(seq)
                
                
            elif packet_type == "start":
                seq_order.append(seq+1)
                self.ack_sender(seq)
                seq_list.append(seq)
                    
                                
                
            elif packet_type == "data":
                # if seq_order[-1] == seq:
                seq_order.append(seq+1)
                seq_list.append(seq)
                self.ack_sender(seq)
                self.data_queue.put(data)
                    
                    
                               
                
            elif packet_type == "end":
                # if seq_order[-1] == seq:
                self.ack_sender(seq)
                seq_order = []
                seq_list = []
                string = ""

                if self.data_queue.qsize() > 1:
                    string = self.concatenator()
                else:
                    string = self.data_queue.get()
        

                self.command_handler(string)
                # to terminate the loop when client disconnects
                if self.exit:
                    loop = False
                    break
                
                
        self.exit = False
                

                
                
                
                
                

    def send_response(self, msg_type, type_no, msg = None ):
        global ack_queue
        global lost_pkt
        global loop
        
        # print('send response--------------------')
        sq = random.randint(0,2000)
        ret = 0 # controls the retransmission
        
        # sending Start packet
        while(ret <= util.NUM_OF_RETRANSMISSIONS):

            try:
                start_packet = util.make_packet("start", sq)
                self.sock.sendto(start_packet.encode("utf-8"), (self.server_addr,self.server_port))
                # print('start:', sq)
                sq = ack_queue.get(timeout= util.TIME_OUT)
                break
            except:
                ret = ret + 1

        # # sending data packet 

        temp_msg = util.make_message(msg_type, type_no, msg)
        ret = 0
        
        # Case where message is greater the chunk size
        if len(temp_msg) > util.CHUNK_SIZE:
            n = util.CHUNK_SIZE - 1
            chunk_list = [temp_msg[i:i+n] for i in range(0, len(temp_msg), n)]
            
            for x in chunk_list:
                while(ret <= util.NUM_OF_RETRANSMISSIONS):
                    try:
                        pkt = util.make_packet("data", sq, x)
                        self.sock.sendto(pkt.encode("utf-8"), (self.server_addr,self.server_port))
                        sq = ack_queue.get(timeout= util.TIME_OUT)
                        break
                    except:
                        ret = ret + 1
        
        else: 
            while ret <= util.NUM_OF_RETRANSMISSIONS:
                try:
                    data_packet = util.final_msg(msg_type, type_no, msg, "data", sq)
                    self.sock.sendto(data_packet.encode("utf-8"), (self.server_addr,self.server_port))
                    # print('data:', sq)
                    sq = ack_queue.get(timeout= util.TIME_OUT)
                    break
                except:
                    ret = ret + 1 
            
        # sending End packet
        end_packet = util.make_packet("end", sq)
        self.sock.sendto(end_packet.encode("utf-8"), (self.server_addr,self.server_port))
        # print('end:', sq)

        
        # waits for end packet ack
        try:
            _ = ack_queue.get(timeout= util.TIME_OUT)
        except:
            pass
            
        
    
        
        
    def ack_sender(self, seq):
        packet = util.make_packet("ack", seq+1)
        self.sock.sendto(packet.encode("utf-8"), (self.server_addr, self.server_port))
        
    
    def command_handler(self, data):
        data_list = data.split()

        if "err_username_unavailable" in data:
            print("disconnected: username not available")
            self.exit = True
            
        elif "err_server_full" in data:
            print("disconnected: server full")
            self.exit = True
            
        elif "response_users_list" in data:
            # removes the data and length because these are not anymore useful
            del data_list[0:2]
            print("list:" , " ".join(data_list))
            
        elif "forward_message" in data:
            del data_list[0:2]
            sender_name = data_list[-1]
            del data_list[-1]
            # now the data_list contains only the actual msg
            print("msg:", sender_name + ":", " ".join(data_list))
            
        elif "forward_file" in data:
            del data_list[0:2] # delete msg type and msg length
            file_name = data_list[0]
            del data_list[0] # delete file name from the msg
            sender_name = util.get_name(data)
            del data_list[-1] # delete sender name
            file_data = " ".join(data_list)
            
            with open(self.name + "_" + file_name, "w") as f:
                f.write(file_data)
                
            print("file: " + sender_name + ": " + file_name)
            
        elif "err_unknown_message" in data:
            print("disconnected: server received an unknown command")
            self.exit = True


    def concatenator(self):
        string = ""
        while not self.data_queue.empty():
            string = string + self.data_queue.get()

        return string

# Do not change this part of code
if __name__ == "__main__":
    def helper():
        '''
        This function is just for the sake of our Client module completion
        '''
        print("Client")
        print("-u username | --user=username The username of Client")
        print("-p PORT | --port=PORT The server port, defaults to 15000")
        print("-a ADDRESS | --address=ADDRESS The server ip or hostname, defaults to localhost")
        print("-w WINDOW_SIZE | --window=WINDOW_SIZE The window_size, defaults to 3")
        print("-h | --help Print this help")
    try:
        OPTS, ARGS = getopt.getopt(sys.argv[1:],
                                   "u:p:a:w", ["user=", "port=", "address=","window="])
    except getopt.error:
        helper()
        exit(1)

    PORT = 15000
    DEST = "localhost"
    USER_NAME = None
    WINDOW_SIZE = 3
    for o, a in OPTS:
        if o in ("-u", "--user="):
            USER_NAME = a
        elif o in ("-p", "--port="):
            PORT = int(a)
        elif o in ("-a", "--address="):
            DEST = a
        elif o in ("-w", "--window="):
            WINDOW_SIZE = a

    if USER_NAME is None:
        print("Missing Username.")
        helper()
        exit(1)

    S = Client(USER_NAME, DEST, PORT, WINDOW_SIZE)
    try:
        # Start receiving Messages
        T = Thread(target=S.receive_handler)
        T.daemon = True
        T.start()
        # Start Client
        S.start()
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
