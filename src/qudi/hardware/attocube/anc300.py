import serial

port = serial.Serial(port = 'COM9', 
                            baudrate = 38400, 
                            bytesize = serial.EIGHTBITS, 
                            stopbits = serial.STOPBITS_ONE, 
                            timeout=2, 
                            parity=serial.PARITY_NONE)
EOL = "\r\n"


port.write((f"setdci 3 off{EOL}").encode()) #set dc off
returnVal = port.readline()

