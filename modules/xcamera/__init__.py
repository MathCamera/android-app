from camera4kivy import Preview
from gestures4kivy import CommonGestures
from kivy.graphics import Line, Color, Rectangle
from kivy.metrics import dp
from PIL import Image
from kivymd.app import App
from kivy.logger import Logger
from kivy.clock import Clock

class XCamera(Preview, CommonGestures):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def analyze_pixels_callback(self, pixels, image_size, image_pos, scale, mirror):
        pass
        #app_ = App.get_running_app()
        #if app_.root.ids.sm.current == "sc_photo" and app_.send_state==False:
        #    Logger.info("XCamera: sending image...")
        #    pil_image = Image.frombytes(mode='RGBA', size=image_size, data= pixels)
            #app_.handle_image(as_image=True,img=pil_image)

    def canvas_instructions_callback(self, texture, tex_size, tex_pos):#Отображение рамки
        #if App.get_running_app().settings['enable_help_frame']['mode'] == True:
        camera_width,camera_height = tex_size[0] if tex_size[0] >0 else tex_size[0]*(-1),tex_size[1] if tex_size[1] >0 else tex_size[1]*(-1)
        Color(255,0,0,0.6)
        widget_width = camera_width/6*4
        widget_height = camera_height/8
        widget_x = (camera_width/2) - (widget_width/2)
        widget_y = ((camera_height/3)*2) - widget_height
        Line(rectangle=(widget_x,widget_y,widget_width,widget_height),width=dp(2))
        self.frame_data = {"x":widget_x,"y":widget_y,"width":widget_width,"height":widget_height}