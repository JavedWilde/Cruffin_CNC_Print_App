import time
from kivy.app import App
from kivy.lang import Builder
from kivy.utils import platform
from kivy.factory import Factory
from kivy.clock import Clock, mainthread
import threading
import Helpers

if platform == 'android':
    from usb4a import usb
    from usbserial4a import serial4a
else:
    from serial.tools import list_ports
    from serial import Serial

class LongpressButton(Factory.Button):
    __events__ = ('on_long_press', )

    long_press_time = Factory.NumericProperty(1)
    
    def on_state(self, instance, value):
        if value == 'down':
            lpt = self.long_press_time
            self._clockev = Clock.schedule_once(self._do_long_press, lpt)
        else:
            self._clockev.cancel()

    def _do_long_press(self, dt):
        self.dispatch('on_long_press')
        
    def on_long_press(self, *largs):
        pass

class MyPausableThread(threading.Thread):

    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}):
        self._event = threading.Event()
        if target:
            args = ((lambda: self._event.wait()),) + args
        super(MyPausableThread, self).__init__(group, target, name, args, kwargs)

    def pause(self):
        self._event.clear()

    def resume(self):
        self._event.set()


class MainApp(App):
    # BASE PROGRAM
    def __init__(self, *args, **kwargs):
        self.usb_device = None
        self.serial_port = None
        self.uiDict = {}
        self.read_thread = None
        self.port_thread_lock = threading.Lock()
        self.status_thread = None
        self.machine_status = 'Alarm'
        super(MainApp, self).__init__(*args, **kwargs)
    
    def build(self):
        return Builder.load_file('custom_ui.kv')

    def on_button_connect(self):
        if platform == 'android':
            if len(usb.get_usb_device_list())<1:
                self.uiDict['connecterror'].text = 'No device found, make sure the connections are fine.'
                return
            try:
                self.usb_device = usb.get_usb_device_list()[0]
                if not usb.has_usb_permission(self.usb_device):
                    usb.request_usb_permission(self.usb_device)
                    return
                self.serial_port = serial4a.get_serial_port(
                    self.usb_device,
                    115200,
                    8,
                    'N',
                    1,
                    timeout=1
                )
                
            except Exception as e:
                self.uiDict['connecterror'].text = str(e)
                return
        else:
            if len(list_ports.comports())<2:
                self.uiDict['connecterror'].text = 'No device found, make sure the connections are fine.'
                return
            comport = 1 if list_ports.comports()[0].device == 'COM1' else 0
            try:
                self.usb_device = list_ports.comports()[comport].device
                self.serial_port = Serial(
                    self.usb_device,
                    115200,
                    8,
                    'N',
                    1,
                    timeout=1
                )
                
            except Exception as e:
                self.uiDict['connecterror'].text = str(e)
                return
            
        print(self.serial_port)
        if self.serial_port.is_open and not self.read_thread:
            self.read_thread = MyPausableThread(target=self.read_msg_thread)
            self.read_thread.daemon = True
            self.read_thread.start()
            self.read_thread.resume()

            self.status_thread = MyPausableThread(target=self.request_status_thread)
            self.status_thread.daemon = True
            self.status_thread.start()
            self.status_thread.resume()
        else:
            self.uiDict['connecterror'].text = 'Connection Error, make sure the right device is connected.'
            return
        self.uiDict['sm'].current = 'main'
 
    def on_stop(self):
        if self.serial_port:
            with self.port_thread_lock:
                self.serial_port.close()
    
        
            
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
        self.uiDict['status'].text = stat[0]
        self.uiDict['status'].background_color = stat[1]

    # THREADS
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
                    self.display_msg_thread(msg)
            except Exception as e:
                self.display_msg_thread(str(e))
                raise e
    
    def homing_thread(self):
        self.status_thread.pause()
        self.update_status('Homing')
        self.send_command('$X')
        time.sleep(1)
        self.send_command('G0F1000Z1')
        time.sleep(1)
        self.send_command('$H')
        time.sleep(1)
        self.status_thread.resume()

    @mainthread
    def display_msg_thread(self,msg):
        if msg.strip().startswith('<'):
            self.update_status(msg.strip()[1:-1].split('|')[0])
        else:
            self.uiDict['output'].text += msg
        self.uiDict['developeroutput'].text += msg

    @mainthread
    def send_command(self, command):
        data = bytes(
                (command + '\n'),
                'utf8'
            )
        self.serial_port.write(data)
        self.uiDict['output'].text += f'[Sent] {command}\n'
      

    # BUTTON ACTIONS
    def on_button_start(self):
        fontFile = f'Fonts/SVGFONT ({0}).svg' #change numbers for different fonts, 0 - 18
        gcode = Helpers.GetGcode(self.uiDict['nameinput'].text,fontFile,0,0,0.9,750,750,25,6)
        self.read_thread.pause()
        self.status_thread.pause()

        lines = gcode.split('\n')
        for i ,line in enumerate(lines):
            l = line.strip() # Strip all EOL characters for consistency
            print ('Sending: ' + l),
            self.serial_port.write(bytes(line + '\n','utf8')) # Send g-code block to grbl
            grbl_out = bytes(self.serial_port.readline()).decode('utf8').strip() # Wait for grbl response with carriage return
            print ("Response: " + grbl_out)
        
        self.read_thread.resume()
        self.status_thread.resume()
    
    def on_button_home(self):
        threading.Thread(target=self.homing_thread).start()

    
    def on_button_origin(self):
        self.send_command('G10 P0 L20 X0 Y0 Z0')
        time.sleep(1)
        self.send_command('G0F1000Y60')
    
    def on_button_open_developer_screen(self):
        self.uiDict['sm'].current = 'developer'

    def on_button_developer_send(self):
        self.send_command(self.uiDict['developerinput'].text)
        self.uiDict["developerinput"].text = ''

if __name__ == '__main__':
    MainApp().run()
