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
from kivy.metrics import dp
from kivy.storage.jsonstore import JsonStore
from kivy.graphics.texture import Texture

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

        self.settingUiDict = {}
        self.settings_storage = JsonStore('_settings.json')
        self.machine_settings = self.settings_storage.get('machine_settings')[
            'settings']

        self.padding = [self.machine_settings['xpadding_int'],
                        self.machine_settings['ypadding_int']]
        print(self.padding)

        super(MainApp, self).__init__(*args, **kwargs)

    def build(self):
        LabelBase.register(name='Lexend-Medium',
                           fn_regular='UiFonts/Lexend/Lexend-Medium.ttf')
        return Builder.load_file('main_ui.kv')

    def on_stop(self):
        if self.serial_port:
            with self.port_thread_lock:
                self.serial_port.close()

    # Helpers--------------------------------------------------------------------------

    def update_settings_ui(self):
        self.machine_settings = self.settings_storage.get('machine_settings')[
            'settings']
        for setting in self.settingUiDict.keys():
            self.settingUiDict[setting].text = str(
                self.machine_settings[setting])
        self.padding = [self.machine_settings['xpadding_int'],
                        self.machine_settings['ypadding_int']]
        

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
        self.send_command(f"G0F1000Y{self.machine_settings['bedout_int']}")
        time.sleep(1)

    def get_gcode(self, border=False):
        stroke = self.machine_settings['doublestrokefile_int'] if self.uiDict[
            'stroke'].active else self.machine_settings['singlestrokefile_int']
        gcode = Helpers.GetGcode(
            self.uiDict['nameinput'].text,
            stroke,
            self.machine_settings['xoffset_flt'],
            self.machine_settings['yoffset_flt'],
            self.machine_settings['scale_flt'],
            self.machine_settings['movespeed_int'],
            self.machine_settings['cutspeed_int'],
            self.machine_settings['letterlimit_int'],
            self.machine_settings['wordwraplimit_int'],
            border,
            self.machine_settings['bedsizex_int'],
            self.machine_settings['bedsizey_int'],
            self.padding[0],
            self.padding[1],
            self.machine_settings['bedout_int'])
        return gcode, stroke

    def update_status(self, status):
        status_lookup = {
            'Alarm': ['Press Home', [0.75, 0, 0, 1]],
            'Origin': ['Press Reset Origin', [0.75, 0, 0, 1]],
            'Idle': ['Ready', [0, 0.75, 0, 1]],
            'Run': ['Moving', [0.75, 0, 0, 1]],
            'Jog': ['Homing Required', [0.75, 0, 0, 1]],
            'Homing': ['Homing Device', [0, 0, 0.75, 1]],
            'Home': ['Homing Device', [0, 0, 0.75, 1]],
            'Check': ['Check', [1, 1, 1, 1]],
            'Cycle': ['Cycle', [1, 1, 1, 1]],
            'Hold': ['On Hold', [0, 0.75, 0.75, 1]],
            'Sleep': ['Sleep', [1, 1, 1, 1]]
        }
        self.machine_status = status
        stat = status_lookup[self.machine_status]
        # self.uiDict['status'].text = stat[0]
        # self.uiDict['status'].background_color = stat[1]

    def establish_connection(self, run_startup=True):
        if self.serial_port:
            return

        if platform == 'android':
            if len(usb.get_usb_device_list()) < 1:
                self.show_dialogue_box(
                    '\nNo device found, make sure the connections are fine. Try taking out the usb cable and putting it in again.')
                return
            try:
                usb_device = usb.get_usb_device_list()[0]
                if not usb_device:
                    raise SerialException(
                        "Device {} not present!".format(
                            usb_device.getDeviceName())
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
                self.show_dialogue_box(str(e))
                return
        else:
            if len(list_ports.comports()) < 1:
                self.show_dialogue_box(
                    '\nNo device found, make sure the connections are fine. Try taking out the usb cable and putting it in again.')
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

            self.status_thread = MyPausableThread(
                target=self.request_status_thread)
            self.status_thread.daemon = True

            threading.Thread(target=self.check_grbl_thread,
                             daemon=True, args=(run_startup,)).start()
        else:
            self.show_dialogue_box(
                'Connection Error, make sure the right device is connected.')
            return

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
                    received_msg = self.serial_port.readline()  # read(self.serial_port.in_waiting)
                if received_msg:
                    msg = bytes(received_msg).decode('utf8')
                    self.handle_message(msg)
            except Exception as e:
                self.show_dialogue_box(str(e))
                raise e

    def check_grbl_thread(self, run_startup=True):
        print('checking for grbl')
        if run_startup:
            self.set_connection_log('checking connection...')
            self.set_screen('connecting')
        time.sleep(0.5)
        for _ in range(0, 500):
            if self.machine_connected:
                print('grbl detected')
                self.set_connection_log('connection detected')
                self.set_connection_indicator()
                time.sleep(0.1)
                if run_startup:
                    threading.Thread(
                        target=self.setup_machine_thread, daemon=True).start()
                return
            time.sleep(0.01)

        # handle no connection
        self.show_dialogue_box(
            'Connection not established, port is already in use.\nTake out the usb cable of the phone and plug in again.')
        self.set_screen('connect', 'right')

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
        start = time.time()
        self.set_printing_log('Generating Gcode...')
        self.update_progress_bar(100)

        try:
            gcode, stroke = self.get_gcode()
        except Exception as e:
            self.show_dialogue_box(str(e))
            self.set_screen('main')
            return

        self.set_printing_log('Printing...')
        self.read_thread.pause()
        self.status_thread.pause()

        lines = gcode.split('\n')
        total_lines = len(lines)
        for i, line in enumerate(lines):
            if self.canceling_print:
                break
            l = line.strip()  # Strip all EOL characters for consistency
            # Send g-code block to grbl
            self.serial_port.write(bytes(l + '\n', 'utf8'))
            grbl_out = bytes(self.serial_port.readline()).decode(
                'utf8').strip()  # Wait for grbl response with carriage return
            print(grbl_out)
            # self.update_progress_bar(int((i/total_lines) * 100))

        if self.canceling_print:
            self.set_printing_log('Cancelling...')
            self.set_cancel_button('Icons/please_wait.png')
            time.sleep(1)
            self.send_command('G0F1000Z1')
            time.sleep(1)
            self.send_command(f"G0F1000Y{self.machine_settings['bedout_int']}")
            time.sleep(1)
        else:
            self.set_printing_log(f'Done, Unloading...')

        self.status_thread.resume()
        self.read_thread.resume()
        time.sleep(2)
        while True:
            if self.machine_status == 'Idle':
                self.canceling_print = False
                self.set_cancel_button('Icons/cancel_button_up.png')
                self.set_screen('main', 'right')
                self.show_dialogue_box(
                    f'\nMsg:\n{self.uiDict["nameinput"].text}\n\nTime:\n{time.time()-start:.2f} seconds\n\nFontId:\nSVG_FONT{stroke}', 'Last Print Info')
                self.clear_name_input_field()
                self.status_thread.pause()
                break
        self.status_thread.pause()

    # Main Thread Transfer Functions
    @mainthread
    def clear_name_input_field(self):
        self.uiDict['nameinput'].text = ''

    @mainthread
    def handle_message(self, msg):
        if msg.strip().startswith('<'):
            self.update_status(msg.strip()[1:-1].split('|')[0])
        elif '$X' in msg.strip():
            print('activation msg :' + msg)
            self.uiDict['developeroutput'].text += msg
            self.machine_connected = True
        if msg.strip() != 'ok':
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
    def set_screen(self, screenname, direction='left'):
        self.uiDict['sm'].transition = SlideTransition(
            direction=direction, duration=.25)
        self.uiDict['sm'].current = screenname

    @mainthread
    def set_connection_log(self, text):
        self.uiDict['connectionlog'].text = text

    @mainthread
    def set_printing_log(self, text):
        self.uiDict['printstatus'].text = text

    @mainthread
    def disable_spinner(self):
        self.uiDict['spinner'].active = False

    @mainthread
    def set_cancel_button(self, path):
        self.uiDict['cancelbutton'].source = path

    @mainthread
    def update_progress_bar(self, value):
        self.uiDict['progress'].value = value

    @mainthread
    def set_connection_indicator(self):
        self.uiDict['connectionstatus'].source = 'Icons/connected.png'

    @mainthread
    def show_dialogue_box(self, text, header='Error'):
        if not self.dialog_box:
            self.dialog_box = MDDialog(buttons=[MDFlatButton(
                text="Close",
                theme_text_color="Custom",
                text_color=[0, 0, 0, 1], on_release=lambda *args: self.dialog_box.dismiss()
            )])
        self.dialog_box.title = header
        self.dialog_box.text = text
        self.dialog_box.open()

    # BUTTON ACTIONS
    def on_button_connect(self):
        self.establish_connection()

    def on_button_print(self):
        if not self.uiDict['nameinput'].text or len(self.uiDict['nameinput'].text) > self.machine_settings['letterlimit_int']:
            self.show_dialogue_box(
                f"Name field cannot be empty or over {self.machine_settings['letterlimit_int']} letters.")
            return

        if self.uiDict['previewswitch'].active and self.uiDict['sm'].current != 'preview':
            img = Helpers.plot_gcode_kivy_texture(self.get_gcode(True)[0])
            w, h, _ = img.shape
            texture = Texture.create(size=(h, w), colorfmt='rgba')
            texture.blit_buffer(
                img.flatten(), colorfmt='rgba', bufferfmt='ubyte')
            self.uiDict['previewimage'].texture = texture
            self.uiDict['xpadding'].text = str(self.padding[0])
            self.uiDict['ypadding'].text = str(self.padding[1])
            self.set_screen('preview')
        else:
            threading.Thread(target=self.printing_thread, daemon=True).start()

    def on_button_regenerate(self):
        try:
            self.padding[0] = int(self.uiDict['xpadding'].text)
            self.padding[1] = int(self.uiDict['ypadding'].text)
        except Exception as e:
            self.show_dialogue_box(str(e))
            return
        img = Helpers.plot_gcode_kivy_texture(self.get_gcode(True)[0])
        w, h, _ = img.shape
        texture = Texture.create(size=(h, w), colorfmt='rgba')
        texture.blit_buffer(img.flatten(), colorfmt='rgba', bufferfmt='ubyte')
        self.uiDict['previewimage'].texture = texture

    def on_button_reset(self):
        self.show_dialogue_box(
            'Please close the app, disconnect the usb cable from the phone and reconnect it, thats the best way to reset for now :)', 'Info')

    def on_button_print_cancel(self):
        if not self.canceling_print:
            self.canceling_print = True

    def on_button_open_developer_screen(self):
        self.establish_connection(False)
        self.set_screen('developer')

    def on_button_print_usb_device_list(self):
        if platform == 'android':
            usb_devices = usb.get_usb_device_list()
            for usb_device in usb_devices:
                if not usb_device:
                    self.show_dialogue_box(
                        "Device {} not present!".format(
                            usb_device.getDeviceName())
                    )
                    return
                if not usb.has_usb_permission(usb_device):
                    usb.request_usb_permission(usb_device)
                    return

            for x in usb_devices:
                self.uiDict['developeroutput'].text += f"{x} - {x.getDeviceName()}\n"
        else:
            for com in list_ports.comports():
                self.uiDict['developeroutput'].text += f"{com} - {com.device}\n"

    def on_button_save_settings(self):
        dict = {}
        for key, value in self.settingUiDict.items():
            try:
                if key.split('_')[1] == "flt":
                    dict[key] = float(value.text)
                else:
                    dict[key] = int(value.text)
            except Exception as e:
                self.show_dialogue_box(f"{key} : \n{e}")
                break
        self.settings_storage.put('machine_settings', settings=dict)
        self.update_settings_ui()
        self.uiDict['nameinput'].max_text_length = self.machine_settings['letterlimit_int']
        self.show_dialogue_box(text='Settings Saved', header='Info')


if __name__ == '__main__':
    MainApp().run()
