from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.core.window import Window
from KivyCustom import ImageButton, LongpressButton

factor = 1
Window.size = (int(390/factor),int(866/factor))

class MainApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.uiDict = {}

    def build(self):
        return Builder.load_file('test_ui.kv')
    
    

if __name__ == '__main__':
    MainApp().run()