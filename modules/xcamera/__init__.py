from camera4kivy import Preview
from gestures4kivy import CommonGestures
from kivy.graphics import Line, Color, Rectangle
from kivy.metrics import dp
from PIL import Image

from kivy.logger import Logger

class XCamera(Preview, CommonGestures):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def analyze_pixels_callback(self, pixels, image_size, image_pos, scale, mirror):
        pass

    def canvas_instructions_callback(self, texture, tex_size, tex_pos):
        camera_width,camera_height = tex_size[0] if tex_size[0] >0 else tex_size[0]*(-1),tex_size[1] if tex_size[1] >0 else tex_size[1]*(-1)
        Color(255,0,0,1)
        #Logger.info(f"Camera size: {camera_width}/{camera_height}")
        widget_width = camera_width/6*4
        widget_height = camera_height/8
        widget_x = (camera_width/2) - (widget_width/2)
        widget_y = ((camera_height/3)*2) - widget_height
        Line(rectangle=(widget_x,widget_y,widget_width,widget_height),width=dp(2))
        self.frame_data = {"x":widget_x,"y":widget_y,"width":widget_width,"height":widget_height}