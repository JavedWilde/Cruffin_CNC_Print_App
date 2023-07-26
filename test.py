from kivy.app import App
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior


class MyButton(ButtonBehavior, Image):
    def __init__(self, **kwargs):
        self.uiDict = {}
        super(MyButton, self).__init__(**kwargs)

    def on_press(self):
        pass

    def on_release(self):
        pass