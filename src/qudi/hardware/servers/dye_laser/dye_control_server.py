import socketserver
import time, pickle, dye_control
import numpy as np

class Handler_TCPServer(socketserver.BaseRequestHandler):
    """
    The TCP Server class for demonstration.

    Note: We need to implement the Handle method to exchange data
    with TCP client.

    """

    def handle(self):
        # self.request - TCP socket connected to the client
        
        # print("{} sent smth".format(self.client_address[0]))
        self.api_ = {'set_thin_etalon_voltage': self.set_thin_etalon_voltage, 
        'set_motor_direction': self.set_motor_direction, 
        'move_motor_pulse': self.move_motor_pulse,
        'get_server_time': self.get_server_time
        }
        
        self.data = self.request.recv(1024).strip()
        option = self.data.decode()
        if option in self.api_.keys():
            self.api_[option]()
        else:
            self.unknown()
        
    def move_motor_pulse(self):
        dlc.move_motor_pulse()
        self.send_object("pulsed the motor")

    def set_thin_etalon_voltage(self):
        self.send_object("What the voltage?", flag='k')
        voltage = self.request.recv(1024).decode()
        print("Thin eta voltage", voltage)
        dlc.set_thin_etalon_voltage(float(voltage))

    def set_motor_direction(self):
        self.send_object("What is the direction of the motor?", flag='k')
        direction = self.request.recv(1024).decode()
        dlc.set_motor_direction(int(direction))

    def get_server_time(self):
        self.send_object(time.time(), flag='u')
    
    def unknown(self):
        self.send_object(f"No command. Try one of these {self.api_.keys()}")
        
    def send_object(self, obj, flag = 'u'):
        msg = pickle.dumps(obj)
        msg = flag.encode() + msg
        self.request.sendall(msg)

if __name__ == "__main__":
    HOST, PORT = "0.0.0.0", 1243
    dlc = dye_control.DyeLaserController()
    time_ = time.time()
    # Init the TCP server object, bind it to the localhost on 9999 port
    tcp_server = socketserver.TCPServer((HOST, PORT), Handler_TCPServer)
    # Activate the TCP server.
    # To abort the TCP server, press Ctrl-C.
    tcp_server.serve_forever()
