import random
import time
import Helpers
import re
from matplotlib import pyplot as plt
from serial.tools import list_ports
from serial import Serial
import threading
from Helpers import MyPausableThread

greeting_messages = [
    "Happy birthday to you",
    "Cheers to your retirement",
    "Enjoy your special day",
    "Wishing you love and joy",
    "Merry Christmas dear friend",
    "Happy new year to you",
    "Have a great anniversary",
    "Happy Thanksgiving everyone",
    "Have a lovely Easter",
    "Enjoy your graduation day",
    "Have a warm Hanukkah",
    "Have a joyful Kwanzaa",
    "Happy Diwali to you",
    "Eid Mubarak my friend",
    "Happy Chinese New Year",
    "Have an amazing day",
    "Celebrate your achievements",
    "Happy first day at work",
    "Best wishes on promotion",
    "Stay blessed always",
    "Love on Valentine's Day",
    "Success on your venture",
    "Happy Mother's Day mom",
    "Happy Father's Day dad",
    "Happy Siblings Day bro",
    "Happy Women's Day to you",
    "Wishing a lovely Halloween",
    "Happy Name Day to you",
    "Well done on your success",
    "Congrats on your graduation",
    "Best wishes for baby shower",
    "Happy Healthy Heart Day",
    "Enjoy your house warming",
    "Proud of your achievement",
    "Happy Veteran's Day dad",
    "Happy Labor Day to you",
    "Happy Flag Day everyone",
    "Wishing a peaceful Memorial Day",
    "Happy Indigenous People's Day",
    "Pleased with your success",
    "Happy Friendship Day buddy",
    "Happy Fourth of July",
    "Happy Patriot Day dad",
    "Great job on the promotion",
    "Happy Presidents Day",
    "Have a sweet Valentine's",
    "Wishing a joyful life",
    "Happy Cinco de Mayo",
    "Happy Palm Sunday to you",
    "Happy Rose Day sweetheart",
    "Wishing a blessed life",
    "Happy Rustic Day",
    "Happy Holi to all",
    "Have a memorable trip",
    "Success on your launch",
    "Warm wishes this Christmas",
    "Happy Yom Kippur dad",
    "Happy Rosh Hashanah mom",
    "Celebrate every Earth Day",
    "Enjoy your reunion party",
    "Congrats on a job well done",
    "Wishing a blessed Ramadan",
    "Happy Pongal to you",
    "Enjoy your new journey",
    "Happy to celebrate together",
    "Enjoy your farewell party",
    "Congrats on your engagement",
    "Congrats on your wedding",
    "Happy Martin Luther Day",
    "Happy Bastille Day to all",
    "Have a happy weekend",
    "Happy Spring Day everyone",
    "Happy Earth Hour to all",
    "Happy Arbor Day everyone",
    "Wishing a pleasant summer",
    "Happy Teacher's Day sir",
    "Wishing a beautiful autumn",
    "Happy Children's Day kids",
    "Wishing a blessed Lent",
    "Let's celebrate this day",
    "Have a delightful picnic",
    "Create amazing Halloween memories",
    "Happy St Patrick's Day",
    "Happy Boxing Day all",
    "Welcome December with joy",
    "Celebrate the victory",
    "Happy Canada Day friend",
    "Happy Good Friday everyone",
    "Happy Hanukkah to everyone",
    "Best wishes for now",
    "Keep up the good work",
    "Bask in your achievement",
    "Good luck on your journey",
    "Happy Tu Bishvat friends",
    "Happy Passover to you",
    "Welcome the newborn baby",
    "Congrats on your achievement",
    "Wishing a merry time",
    "Happy Sweetest Day dear",
    "Congrats on your award",
]


def parse_gcode(gcode_text):
    x, y, z = 0, 0, 0
    x_values, y_values = [], []
    pen_down = False

    gcode_commands = re.findall(
        r"[Gg]\d+\s?(?:[Ff]\d+)?\s?(?:[Xx]?(-?\d+\.?\d*)\s?)?(?:[Yy]?(-?\d+\.?\d*)\s?)?(?:[Zz]?(-?\d+\.?\d*))?[;]?",
        gcode_text,
    )
    for command in gcode_commands:
        if command[0]:
            x = float(command[0])
        if command[1]:
            y = float(command[1])
        if command[2]:
            z = float(command[2])
            if z < 0:
                pen_down = True
            elif z > 0:
                pen_down = False
        if pen_down and (command[0] or command[1] or command[2]):
            x_values.append(x)
            y_values.append(y)
        elif not pen_down:
            x_values.append(None)
            y_values.append(None)

    return x_values, y_values


def plot_gcode_preview(gcode_text, filename):
    x_values, y_values = parse_gcode(gcode_text)

    fig, ax = plt.subplots()

    # Calculate the data range for x and y
    x_range = max(x for x in x_values if x is not None) - min(
        x for x in x_values if x is not None
    )
    y_range = max(y for y in y_values if y is not None) - min(
        y for y in y_values if y is not None
    )

    # Set the figure size based on the data range
    fig.set_size_inches(x_range * 0.1, y_range * 0.1)
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

    ax.plot(x_values, y_values, "b-")  # Set the line color to white
    ax.set_xlim(
        min(x for x in x_values if x is not None),
        max(x for x in x_values if x is not None),
    )
    ax.set_ylim(
        min(y for y in y_values if y is not None),
        max(y for y in y_values if y is not None),
    )

    ax.set_xticks([])  # Remove x-axis ticks and labels
    ax.set_yticks([])  # Remove y-axis ticks and labels

    # Set the background color for the saved image
    plt.savefig(filename, facecolor="black")
    plt.close()

def Test_Gcode_Generator():
    for i, msg in enumerate(greeting_messages):
        if len(msg) > 25:
            msg = msg[:24]
        msg = msg[:random.randrange(1, 24)]
        if msg[-1] == ' ':
            msg = msg[:-1]

        gcode = Helpers.GetGcode(
            msg, 4, 0, 0, 1, 750, 750, 25, 10, True, 70, 40, 3, 3
        )
        plot_gcode_preview(gcode, f"_FontPreview/{i}.png")

def send_command(command):
        print(command)
        global serial_port
        data = bytes(
            (command + '\n'),
            'utf8'
        )
        serial_port.write(data)

def read_msg_thread(pause_checker):
        global serial_port
        while True:
            pause_checker()
            try:
                received_msg = serial_port.readline()  # read(self.serial_port.in_waiting)
                if received_msg:
                    msg = bytes(received_msg).decode('utf8')
                    print(msg)
            except Exception as e:
                print(str(e))
                raise e

def Run_Printer_Stress_Test():
    pos_list = []
    gcode_list = []
    max = 60
    divisions = 10
    for x in range(divisions+1):
        val = (x/divisions) * max
        if x%2 == 0:
            pos_list.append((val,0))
            pos_list.append((val,max))
        else:
            pos_list.append((val,max))
            pos_list.append((val,0))
    gcode = 'G0F1000Z-1;\n'
    for x in pos_list:
         gcode += f'G1F750X{x[0]}Y{x[1]};\n'

    for x in pos_list:
         gcode += f'G1F750X{x[1]}Y{x[0]};\n'
    
    temp = gcode
    for x in range(10):
         gcode+=temp
         
    gcode+= 'G0F1000Z1;\nG0F750X10Y85;'
    gcode_list.append(gcode)
    with open('test.gcode','w+') as f:
        f.write(gcode)       

    # for i, msg in enumerate(greeting_messages):
    #     if len(msg) > 25:
    #         msg = msg[:24]
    #     msg = msg[:random.randrange(1, 24)]
    #     if msg[-1] == ' ':
    #         msg = msg[:-1]

    #     gcode = Helpers.GetGcode(
    #         msg, 4, 0, 0, 1, 750, 750, 25, 10, True, 70, 40, 3, 3
    #     )
    #     print(f'Added index {i}')
    #     gcode_list.append(gcode)


    global serial_port
    read_thread = None
    try:
        port = int(input(f'{[x.device for x in list_ports.comports()]}\nInsert port index - '))
    except Exception as e:
        print(e)
        return
    print(list_ports.comports()[port])
    try:
                usb_device = list_ports.comports()[port].device
                serial_port = Serial(
                    usb_device,
                    115200,
                    8,
                    'N',
                    1,
                    timeout=1
                )

    except Exception as e:
        print(str(e))
        return
    
    if serial_port.is_open:
        read_thread = MyPausableThread(target=read_msg_thread)
        read_thread.daemon = True
        read_thread.start()
        read_thread.resume()

    print('Homing')
    time.sleep(2)
    send_command("\r\n\r\n")
    time.sleep(1)
    send_command('$X')
    time.sleep(1)
    send_command('G0F1000Z1')
    time.sleep(1)
    send_command('$H')
    time.sleep(1)

    input('Press Enter When Home is Complete.......\n')

    time.sleep(1)
    send_command('G10 P0 L20 X0 Y0 Z1')
    time.sleep(1)
    send_command('G0F1000Y85')
    time.sleep(1)

    input('Load Paper.......\n')
    input('Press Enter to start Stress Test..........\n')

    for gcode in gcode_list:
        start = time.time()
        read_thread.pause()

        lines = gcode.split('\n')
        for i, line in enumerate(lines):
            l = line.strip()
            print(l)
            serial_port.write(bytes(l + '\n', 'utf8'))
            grbl_out = bytes(serial_port.readline()).decode(
                'utf8').strip()
            print(grbl_out)
        print(f'Time Taken : {time.time()-start:.2f}')
        input('Load More Paper and Press Enter to start next print........\n')

    serial_port.close()

    

Run_Printer_Stress_Test()