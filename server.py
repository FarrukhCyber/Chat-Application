'''
This module defines the behaviour of server in your Chat Application
'''
import sys
import getopt
import socket
import util
import random
from threading import Thread
from queue import Queue



class Server:
    '''
    This is the main Server Class. You will to write Server code inside this class.
    '''
    def __init__(self, dest, port, window):
        self.server_addr = dest
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(None)
        self.sock.bind((self.server_addr, self.server_port))
        self.window = window
        # uses user-names as keys and stores info of online users
        self.clients= {} 
        # hold the msg data to process after words
        self.dic_data = {}
        # to check the validity of a seq no
        self.seq_list = []
        # controls the threading for each client
        self.queues = {}
        # to control send response threads
        self.ack_queue = Queue(0)
        # end the receiving thread
        self.exit = False
        self.seq_order = []
        
        



    def start(self):
        
        while True:
            packet, address = self.sock.recvfrom(4096)
            
            if address not in self.queues:
                self.queues[address] = Queue(0)
                T = Thread(target= self.receive_response, args= (packet, address))
                T.daemon = True
                T.start()

               
            self.queues[address].put(packet)


    def command_handler(self, data, address):
        
        data_list = data.split()
        
        if "join" in data:
            name = util.get_name(data)
            
            if len(self.clients) < util.MAX_NUM_CLIENTS:
                if name not in self.clients:
                    self.clients[name] = address
                    print("join:", name)
                else:
                    print("disconnected: username not available")
                    t2 = Thread(target= self.send_response, args= (address, "err_username_unavailable", 2, None))
                    t2.daemon = True
                    t2.start()
   
            else:
                print("disconnected: server full")
                t2 = Thread(target= self.send_response, args= (address, "err_server_full", 2, None))
                t2.daemon = True
                t2.start()
 
                
        elif "request_users_list" in data:
            name = util.key_from_value(self.clients, address)
            
            print("request_users_list:", name)
            
            active_users_list = list(self.clients.keys())
            active_users_list.sort() # sorts the list in ascending order
            
            t2 = Thread(target= self.send_response, args= (address, "response_users_list", 3, " ".join(active_users_list)))
            t2.daemon = True
            t2.start()

            
        elif "disconnect" in data:
            name = util.get_name(data)
            print("disconnected: " + name )
            del self.clients[name]
            self.exit = True
            
        elif "send_message" in data:
            name = util.key_from_value(self.clients, address)
            print("msg:", name)
            del data_list[0:2] # deleteing msg type and msg length
            
            # extracting actual msg, no of recievers and their names
            no_of_rec = int(data_list[0])
            rec = data_list[1:no_of_rec+1]
            del data_list[0:no_of_rec+1]
            actual_msg = " ".join(data_list) + " " + name
            
            #broadcasting
            for x in rec:
                if x in self.clients:
                    t2 = Thread(target= self.send_response, args= (self.clients[x], "forward_message", 4, actual_msg))
                    t2.daemon = True
                    t2.start()                    
                 
                else:
                    print("msg:", name, "to non-existent user", x)
                    
        elif "send_file" in data:
            sender_name = util.key_from_value(self.clients, address)
            print("file: " + sender_name)
            del data_list[0:2] # deleteing msg type and msg length
            
            # extracting actual msg, no of recievers and their names
            no_of_rec = int(data_list[0])
            rec = data_list[1:no_of_rec+1]
            del data_list[0:no_of_rec+1]
    
            # actual_msg will contain file name, file data and sender_name
            actual_msg = " ".join(data_list) + " " + sender_name
            
            #broadcasting
            for x in rec:
                if x in self.clients:
                    t2 = Thread(target= self.send_response, args= (self.clients[x], "forward_file", 4, actual_msg))
                    t2.daemon = True
                    t2.start()
                else:
                    print("file: " + sender_name + " to non-existent user " + x)
        
                    
        else:
            sender_name = util.key_from_value(self.clients, address)
            print("disconnected: " + sender_name + " send unknown command")
            t2 = Thread(target= self.send_response, args= (address, "err_unknown_message", 2, None))
            t2.daemon = True
            t2.start()

        
    def receive_response(self, packet, address):
        
        while True:
            
            packet = self.queues[address].get()
            packet_type, seq, data, _ = util.parse_packet(packet.decode("utf-8"))
            seq = int(seq)
            
            # handling duplicate packets
            # if seq in self.seq_list:
            #     self.ack_sender(seq, address)
            #     continue
                
            # # handling out of order packets
            # if (packet_type != "ack" and self.seq_order and self.seq_order[-1] != seq):
            #     continue
                
            if packet_type == "start":
                self.seq_order.append(seq+1)
                self.seq_list.append(seq)
                self.ack_sender(seq, address)
                self.dic_data[address] = Queue(0)
                    
                
            
            elif packet_type == "data":
                # if self.seq_order[-1] == seq:
                self.seq_order.append(seq+1)
                self.ack_sender(seq, address)
                self.dic_data[address].put(data)    
                self.seq_list.append(seq)
                        
                    
                
                    
            elif packet_type == "end":
                # if self.seq_order[-1] == seq:
                self.ack_sender(seq, address)
                self.seq_list = []
                self.seq_order = []
                
                string = ""
                if self.dic_data[address].qsize() > 1:
                    string = self.concatenator(address)
                else:
                    string = self.dic_data[address].get()
        
                self.command_handler(string, address)
                        

                # when user disconnects end its thread
                if self.exit:
                    break
                    
            elif packet_type == "ack":
                self.ack_queue.put(seq)
                
        self.exit = False
        del self.queues[address]
        
            
        return 



    def send_response(self, address, msg_type, type_no, msg = None ):
        # sequence = random.randint(0,200)
        sq = random.randint(0,2000)
        
        ret = 0 # controls the retransmission        
        # sending Start packet
        while(ret <= util.NUM_OF_RETRANSMISSIONS):

            try:
                start_packet = util.make_packet("start", sq)
                self.sock.sendto(start_packet.encode("utf-8"), address)
                # print('start:', sq)
                sq = self.ack_queue.get(timeout= util.TIME_OUT)
                break
            except:
                ret = ret + 1
                
        
        temp_msg = util.make_message(msg_type, type_no, msg)

        # Case where message is greater the chunk size
        if len(temp_msg) > util.CHUNK_SIZE:
            n = util.CHUNK_SIZE - 1
            chunk_list = [temp_msg[i:i+n] for i in range(0, len(temp_msg), n)]
            ret = 0 # controls the retransmission
            
            for x in chunk_list:
                while(ret <= util.NUM_OF_RETRANSMISSIONS):
                    try:
                        pkt = util.make_packet("data", sq, x)
                        self.sock.sendto(pkt.encode("utf-8"), address)
                        sq = self.ack_queue.get(timeout= util.TIME_OUT)
                        break
                    except:
                        ret = ret + 1
                
        else: 
            while ret <= util.NUM_OF_RETRANSMISSIONS:
                try:
                    data_packet = util.final_msg(msg_type, type_no, msg, "data", sq)
                    self.sock.sendto(data_packet.encode("utf-8"), address)
                    # print('data:', sq)
                    sq = self.ack_queue.get(timeout= util.TIME_OUT)
                    break
                except:
                    ret = ret + 1   
       

        # sending End packet
        end_packet = util.make_packet("end", sq)
        self.sock.sendto(end_packet.encode("utf-8"), address)
        # print('end:', sq)
   
        
        # waits for the end packet ack
        try:
            _ = self.ack_queue.get(timeout= util.TIME_OUT)
        except:
            pass
            
        
        
        return
        
            
              
        
    def ack_sender(self, seq, address):
        packet = util.make_packet("ack", seq+1)
        self.sock.sendto(packet.encode("utf-8"), address)
        
        
    def concatenator(self, address):
        string = ""
        while not self.dic_data[address].empty():
            string = string + self.dic_data[address].get()

        return string
            
        
        
        
# Do not change this part of code

if __name__ == "__main__":
    def helper():
        '''
        This function is just for the sake of our module completion
        '''
        print("Server")
        print("-p PORT | --port=PORT The server port, defaults to 15000")
        print("-a ADDRESS | --address=ADDRESS The server ip or hostname, defaults to localhost")
        print("-w WINDOW | --window=WINDOW The window size, default is 3")
        print("-h | --help Print this help")

    try:
        OPTS, ARGS = getopt.getopt(sys.argv[1:],
                                   "p:a:w", ["port=", "address=","window="])
    except getopt.GetoptError:
        helper()
        exit()

    PORT = 15000
    DEST = "localhost"
    WINDOW = 3

    for o, a in OPTS:
        if o in ("-p", "--port="):
            PORT = int(a)
        elif o in ("-a", "--address="):
            DEST = a
        elif o in ("-w", "--window="):
            WINDOW = a

    SERVER = Server(DEST, PORT,WINDOW)
    try:
        SERVER.start()
    except (KeyboardInterrupt, SystemExit):
        exit()
