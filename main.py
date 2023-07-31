import time
from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.utils import platform
from kivy.clock import mainthread
import threading
from Helpers import MyPausableThread
from kivy.core.text import LabelBase
from kivy.uix.screenmanager import SlideTransition
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton

from serial import SerialException
import Helpers

if platform == 'android':
    from usb4a import usb
    from usbserial4a import serial4a
else:
    from serial.tools import list_ports
    from serial import Serial




class MainApp(MDApp):
    # BASE PROGRAM
    def __init__(self, *args, **kwargs):
        self.serial_port = None
        self.uiDict = {}
        self.port_thread_lock = threading.Lock()
        self.read_thread = None
        self.status_thread = None
        self.machine_status = 'Alarm'
        self.machine_connected = False
        self.canceling_print = False

        self.dialog_box = None
        super(MainApp, self).__init__(*args, **kwargs)
    
    def build(self):
        LabelBase.register(name='Lexend-Medium', fn_regular='UiFonts/Lexend/Lexend-Medium.ttf')
        
        return Builder.load_file('main_ui.kv')

    def on_stop(self):
        if self.serial_port:
            with self.port_thread_lock:
                self.serial_port.close()
    
        
    def home_machine(self):
        time.sleep(2)
        self.send_command("\r\n\r\n")
        time.sleep(1)
        self.send_command('$X')
        time.sleep(1)
        self.send_command('G0F1000Z1')
        time.sleep(1)
        self.send_command('$H')
        time.sleep(1)

    def set_origin(self):
        time.sleep(1)
        self.send_command('G10 P0 L20 X0 Y0 Z1')
        time.sleep(1)
        self.send_command('G0F1000Y60')
        time.sleep(1)

    def update_status(self, status):
        status_lookup = {
            'Alarm' : ['Press Home', [0.75,0,0,1]],
            'Origin' : ['Press Reset Origin', [0.75,0,0,1]],
            'Idle' : ['Ready', [0,0.75,0,1]],
            'Run' : ['Moving', [0.75,0,0,1]],
            'Jog' : ['Homing Required', [0.75,0,0,1]],
            'Homing' : ['Homing Device', [0,0,0.75,1]],
            'Home' : ['Homing Device', [0,0,0.75,1]],
            'Check' : ['Check', [1,1,1,1]],
            'Cycle' : ['Cycle', [1,1,1,1]],
            'Hold' : ['On Hold', [0,0.75,0.75,1]],
            'Sleep' : ['Sleep', [1,1,1,1]]
        }
        self.machine_status = status
        stat = status_lookup[self.machine_status]
        # self.uiDict['status'].text = stat[0]
        # self.uiDict['status'].background_color = stat[1]

    # THREADS------------------------------------------------------------------------
    def request_status_thread(self, pause_checker):
        while True:
            pause_checker()
            self.send_command('?')
            time.sleep(1)

    def read_msg_thread(self, pause_checker):
        while True:
            pause_checker()
            try:
                with self.port_thread_lock:
                    if not self.serial_port.is_open:
                        break
                    received_msg = self.serial_port.readline()#read(self.serial_port.in_waiting)
                if received_msg:
                    msg = bytes(received_msg).decode('utf8')
                    self.handle_message(msg)
            except Exception as e:
                self.show_dialogue_box(str(e))
                raise e
    
    def check_grbl_thread(self):
        print('checking for grbl')
        self.set_screen('connect')
        self.set_connection_log('checking connection...')
        self.set_screen('connecting')
        time.sleep(0.5)
        for i in range(0,1000):
            if self.machine_connected:
                print('grbl detected')
                self.set_connection_log('connection detected')
                self.set_connection_indicator()
                time.sleep(0.1)
                threading.Thread(target=self.setup_machine_thread, daemon=True).start()
                return
            time.sleep(0.01)
        # handle no connection

    def setup_machine_thread(self):
        print('homing')
        self.set_connection_log('Homing...')
        self.update_status('Home')
        self.home_machine()
        self.status_thread.start()
        self.status_thread.resume()
        while True:
            if self.machine_status == 'Idle':
                self.set_connection_log('Home Complete')
                time.sleep(0.1)
                print('home complete')
                self.status_thread.pause()
                break
        
        print('preparing')
        self.set_connection_log('Preparing...')
        self.set_origin()
        self.status_thread.resume()
        time.sleep(2)
        while True:
            if self.machine_status == 'Idle':
                self.set_connection_log('Prepare Complete')
                time.sleep(0.1)
                print('Prepare Complete')
                self.disable_spinner()
                self.status_thread.pause()
                break
        print('ready')
        self.set_connection_log('Ready')
        time.sleep(0.5)
        self.set_screen('main') 

    def printing_thread(self):
        self.set_screen('printing')
        self.set_printing_log('Generating Gcode...')
        self.update_progress_bar(0)
        try:
            fontFile = f'Fonts/SVGFONT ({0}).svg' #change numbers for different fonts, 0 - 18
            gcode = Helpers.GetGcode(self.uiDict['nameinput'].text,fontFile,5,8,0.9,750,750,25,6)
        except Exception as e:
            self.show_dialogue_box(str(e))
            return
        
        self.set_printing_log('Printing...')
        self.read_thread.pause()
        self.status_thread.pause()

        lines = gcode.split('\n')
        total_lines = len(lines)
        for i ,line in enumerate(lines):
            if self.canceling_print:
                break
            l = line.strip() # Strip all EOL characters for consistency
            self.serial_port.write(bytes(l + '\n','utf8')) # Send g-code block to grbl
            grbl_out = bytes(self.serial_port.readline()).decode('utf8').strip() # Wait for grbl response with carriage return
            print(grbl_out)
            self.update_progress_bar(int((i/total_lines) * 100))


        if self.canceling_print:
            self.set_printing_log('Cancelling...')
            self.set_cancel_button('Icons/please_wait.png')
            time.sleep(1)
            self.send_command('G0F1000Z1')
            time.sleep(1)
            self.send_command('G0F1000Y60')
            time.sleep(1)
        else:
            self.set_printing_log('Done, Unloading...')
        
        self.status_thread.resume()
        self.read_thread.resume()
        time.sleep(2)
        while True:
            if self.machine_status == 'Idle':
                self.canceling_print = False
                self.set_cancel_button('Icons/cancel_button_up.png')
                self.set_screen('main','right')
                self.status_thread.pause()
                break

    

    # Main Thread Transfer Functions    
    @mainthread
    def handle_message(self,msg):
        if msg.strip().startswith('<'):
            self.update_status(msg.strip()[1:-1].split('|')[0])
        elif '$X' in msg.strip():
            print('activation msg :' + msg)
            self.uiDict['developeroutput'].text += msg
            self.machine_connected = True
        else:
            if msg.strip() != 'ok':
                #self.uiDict['output'].text += msg
                print(msg)
        self.uiDict['developeroutput'].text += msg

    @mainthread
    def send_command(self, command):
        data = bytes(
                (command + '\n'),
                'utf8'
            )
        self.serial_port.write(data)
        if '?' not in command:
            self.uiDict['developeroutput'].text += f'[Sent] {command}\n'
            print(f'[Sent] {command}\n')
      
    @mainthread
    def set_screen(self,screenname,direction='left'):
        self.uiDict['sm'].transition = SlideTransition(direction=direction, duration=.25)
        self.uiDict['sm'].current = screenname

    @mainthread
    def set_connection_log(self,text):
        self.uiDict['connectionlog'].text = text
    
    @mainthread
    def set_printing_log(self, text):
        self.uiDict['printstatus'].text =  text
    
    @mainthread
    def disable_spinner(self):
        self.uiDict['spinner'].active = False

    @mainthread
    def set_cancel_button(self, path):
        self.uiDict['cancelbutton'].source = path
    
    @mainthread
    def update_progress_bar(self,value):
        self.uiDict['progress'].value = value
    @mainthread
    def set_connection_indicator(self):
        self.uiDict['connectionstatus'].source = 'Icons/connected.png'

    @mainthread
    def show_dialogue_box(self, text):
        if not self.dialog_box:
            self.dialog_box = MDDialog(buttons = [MDFlatButton(
                text="Close",
                theme_text_color="Custom",
                text_color=[0,0,0,1], on_release = lambda *args: self.dialog_box.dismiss()
            )])
        self.dialog_box.title = 'Error'
        self.dialog_box.text = text
        self.dialog_box.open()   
        
    # BUTTON ACTIONS
    def on_button_connect(self):
        if platform == 'android':
            if len(usb.get_usb_device_list())<1:
                self.show_dialogue_box('\nNo device found, make sure the connections are fine. Try taking out the usb cable and putting it in again.')
                return
            try: 
                usb_device = usb.get_usb_device_list()[0]
                if not usb_device:
                    raise SerialException(
                        "Device {} not present!".format(usb_device.getDeviceName())
                    )
                if not usb.has_usb_permission(usb_device):
                    usb.request_usb_permission(usb_device)
                    return
                self.serial_port = serial4a.get_serial_port(
                    usb_device.getDeviceName(),
                    115200,
                    8,
                    'N',
                    1,
                    timeout=1
                )
                
            except Exception as e:
                self.show_dialogue_box (str(e))
                return
        else:
            if len(list_ports.comports())<2:
                self.show_dialogue_box('\nNo device found, make sure the connections are fine. Try taking out the usb cable and putting it in again.')
                return
            comport = 1 if list_ports.comports()[0].device == 'COM1' else 0
            try:
                usb_device = list_ports.comports()[comport].device
                self.serial_port = Serial(
                    usb_device,
                    115200,
                    8,
                    'N',
                    1,
                    timeout=1
                )
                
            except Exception as e:
                self.show_dialogue_box(str(e))
                return
            
        print(self.serial_port)
        if self.serial_port.is_open and not self.read_thread:
            self.read_thread = MyPausableThread(target=self.read_msg_thread)
            self.read_thread.daemon = True
            self.read_thread.start()
            self.read_thread.resume()

            self.status_thread = MyPausableThread(target=self.request_status_thread)
            self.status_thread.daemon = True

            threading.Thread(target=self.check_grbl_thread, daemon=True).start()
        else:
            self.show_dialogue_box('Connection Error, make sure the right device is connected.')
            return
    
    def on_button_print(self):
        if not self.uiDict['nameinput'].text:
            self.show_dialogue_box('Name field cannot be empty. Please enter a name.')
            return
        threading.Thread(target=self.printing_thread, daemon=True).start()
        
    def on_button_print_cancel(self):
            if not self.canceling_print:
                self.canceling_print = True

    def on_button_open_developer_screen(self):
        self.uiDict['sm'].current = 'developer'

    def on_button_developer_send(self):
        self.send_command(self.uiDict['developerinput'].text)
        self.uiDict["developerinput"].text = ''

    

if __name__ == '__main__':
    MainApp().run()
