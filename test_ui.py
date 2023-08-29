import time
from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.core.window import Window
from Helpers import ImageButton, LongpressButton, plot_gcode_kivy_texture
from kivy.uix.screenmanager import SlideTransition
from kivy.core.text import LabelBase
from kivy.graphics.texture import Texture

factor = 3
Window.size = (int(1080/factor), int(2412/factor))
Window.top = 50
Window.left = 0


class MainApp(MDApp):
    def __init__(self, **kwargs):
        self.uiDict = {}
        self.settingUiDict = {}
        super().__init__(**kwargs)

    def build(self):
        LabelBase.register(name='Lexend-Medium',
                           fn_regular='UiFonts/Lexend/Lexend-Medium.ttf')
        self.main_widget = Builder.load_file('main_ui.kv')
        return self.main_widget

    def set_screen(self, screen, direction='left'):
        self.uiDict['sm'].transition = SlideTransition(
            direction=direction, duration=.25)
        self.uiDict['sm'].current = screen

    def load_file_as_string(self, filename):
        with open(filename, 'r') as file:
            file_contents = file.read()
        return file_contents

    # BUTTONS
    def on_button_connect(self):
        self.set_screen('connecting')
        img = plot_gcode_kivy_texture(
            self.load_file_as_string('drawing.gcode'))
        w, h, _ = img.shape
        print(img)
        texture = Texture.create(size=(h, w), colorfmt='rgba')
        texture.blit_buffer(img.flatten(), colorfmt='rgba', bufferfmt='ubyte')
        self.uiDict['previewimage'].texture = texture
        self.set_screen('preview')

    def on_button_print(self):
        self.set_screen('printing')
        pass

    def on_button_reset(self):
        pass


if __name__ == '__main__':
    MainApp().run()
