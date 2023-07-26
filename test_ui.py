import time
from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.core.window import Window
from KivyCustom import ImageButton, LongpressButton
from kivy.uix.screenmanager import SlideTransition
from kivy.core.text import LabelBase

factor = 1
Window.size = (int(390/factor),int(866/factor))

class MainApp(MDApp):
    def __init__(self, **kwargs):
        
        super().__init__(**kwargs)
        self.uiDict = {}

    def build(self):
        LabelBase.register(name='Lexend-Medium', fn_regular='UiFonts/Lexend/Lexend-Medium.ttf')
        self.main_widget = Builder.load_file('test_ui.kv')
        return self.main_widget
    
    def load_screen(self,screen,direction='left'):
        self.main_widget.ids.screenmanager.transition = SlideTransition(direction=direction, duration=.25)
        self.main_widget.ids.screenmanager.current = screen

    # BUTTONS
    def on_button_connect(self):
        self.load_screen('connecting')
        self.load_screen('main')
        
    def on_button_print(self):
        pass
    
    def on_button_reset(self):
        pass

if __name__ == '__main__':
    MainApp().run()