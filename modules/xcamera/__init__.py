from camera4kivy import Preview
from gestures4kivy import CommonGestures

class XCamera(Preview, CommonGestures):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        