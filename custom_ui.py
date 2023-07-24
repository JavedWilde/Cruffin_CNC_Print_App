from kivy.app import App
from kivy.lang import Builder
from kivy.utils import platform

from serial import SerialException

if platform == 'android':
    from usb4a import usb
    from usbserial4a import serial4a
else:
    from serial.tools import list_ports
    from serial import Serial

class MainApp(App):
    def build(self):
        self.usb_device = None
        self.serial_port = None
        self.uiDict = {}
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
        else:
            if len(list_ports.comports())<2:
                self.uiDict['connecterror'].text = 'No device found, make sure the connections are fine.'
                return
            
            try:
                self.usb_device = list_ports.comports()[0].device
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
            print(self.serial_port)

if __name__ == '__main__':
    MainApp().run()
