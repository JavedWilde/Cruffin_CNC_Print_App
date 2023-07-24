from serial import Serial
from serial.tools import list_ports
import time
device_list = [port.device for port in list_ports.comports()]
print(device_list)
device_index = int(input("input index: "))
s = Serial(device_list[device_index],
                     baudrate = 115200,
                     timeout=1
                     )

# Open g-code file
f = open('gcode.gcode','r')

# Wake up grbl
s.write(bytes("$X\n",'utf8'))
time.sleep(1)   # Wait for grbl to initialize
s.write(bytes("$21 = 1\n",'utf8'))
time.sleep(1)   # Wait for grbl to initialize
s.write(bytes("?\n",'utf8')) 
time.sleep(1)   # Wait for grbl to initialize
grbl_out = s.read(s.in_waiting) # Wait for grbl response with carriage return
print (' : ' + bytes(grbl_out).decode('utf8').strip())
s.flushInput()  # Flush startup text in serial input

# Stream g-code to grbl
# for line in f:
#     l = line.strip() # Strip all EOL characters for consistency
#     print ('Sending: ' + l),
#     s.write(bytes(l + '\n','utf8')) # Send g-code block to grbl
#     grbl_out = s.readline() # Wait for grbl response with carriage return
#     print (' : ' + bytes(grbl_out).decode('utf8').strip())

# # Wait here until grbl is finished to close serial port and file.
# input("  Press <Enter> to exit and disable grbl.") 

# Close file and serial port
f.close()
s.close()    