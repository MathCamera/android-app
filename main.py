__version__ = "1.0.0"

from kivy.lang import Builder
from kivy.clock import mainthread
from kivy.utils import platform
from kivy.metrics import dp
from kivy.network.urlrequest import UrlRequest
from kivy.core.window import Window
from kivy.core.clipboard import Clipboard
from kivy.storage.jsonstore import JsonStore
from kivy.loader import Loader
from kivy.logger import Logger

from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton,MDRectangleFlatButton
from kivymd.uix.list import TwoLineListItem,MDList
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.fitimage import FitImage

from modules.android_api import request_camera_permission,set_orientation
from modules.core.update import check_update
from modules.xcamera import *

import base64,os,certifi,urllib.parse,json,webbrowser,shutil
from PIL import Image
from io import BytesIO

if platform == "android":
    from androidstorage4kivy import Chooser,SharedStorage
    from kvdroid.tools import change_statusbar_color,toast,navbar_color
    from kvdroid.tools.darkmode import dark_mode
    change_statusbar_color("#02714C", "white")
else:
    def toast(text):
        print(text)

    def navbar_color(color):
        pass

    def dark_mode():
        return True

    Window.size = (400,700)

class MathCamera(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.version_ = __version__
        self.data_dir = os.path.join("..","user_data")
        self.theme_cls.colors = json.load(open('data/themes.json'))
        self.theme_cls.material_style = "M3"
        self.main_colors = ["#02714C","#039866"]
        self.last_screen,self.flashlight_mode,self.config_ = None,"off",{'config_url':"https://mathcamera-api.vercel.app/config"}

    def build(self):        
        return Builder.load_file('data/md.kv')  
    
    def test():
        print("ok")
    
    def on_start(self):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            self.set_screen("onboarding_sc",root_=True)
    
        self.settings = JsonStore(os.path.join(self.data_dir,'settings.json'))
        self.history = JsonStore(os.path.join(self.data_dir,'history.json'))

        if list(json.load(open('data/settings.json')).keys()) != self.settings.keys():
            self.set_settings(reset=True)

        request_camera_permission()
        set_orientation()
        self.update_config()
        Window.bind(on_keyboard=self.key_handler)
        self.root.ids.preview.connect_camera(enable_video = False,filepath_callback=self.handle_image,enable_analyze_pixels=True,default_zoom=0)
        
        self.theme_cls.theme_style = "Dark" if dark_mode() == True else "Light"
        navbar_color("#121212" if dark_mode() == True else "#FFFFFF")

        if platform == "android":
            self.chooser = Chooser(self.chooser_callback)

        Loader.loading_image = "media/loader-dark.png"#f"media/loader-{self.theme_cls.theme_style.lower()}.png"
        Logger.info(f"App version:{__version__}")

    def on_stop(self):
        self.root.ids.preview.disconnect_camera()
    
    def update_config(self):
        def success(req,result):
            for elem in result.keys():
                self.config_[elem] = result[elem]

            check_update(__version__,result)
            Logger.info(f"Api server response:{result}")
        
        def error(req, result):
            result = str(result).replace("\n","")
            err = f"\n\n{result}" if self.settings["enable_debug_mode"]['mode'] == True else ""
            popup = MDDialog(title='Ошибка',text=f'Не удаётся получить ответ от сервера,\nпроверьте подключение к интернету и повторите попытку{err}',buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color="#02714C",on_release=lambda *args:popup.dismiss()),MDFlatButton(text="Повторить",theme_text_color="Custom",text_color="#02714C",on_release=lambda *args:retry())])
            popup.open()  
            
            def retry():
                popup.dismiss()
                self.update_config()

        req = UrlRequest(self.config_['config_url'],on_success=success,on_failure=error,on_error=error,req_body=urllib.parse.urlencode({'version':self.version_}),req_headers={'Content-type': 'application/x-www-form-urlencoded','Accept': 'text/plain'},ca_file=certifi.where(),verify=True,method='POST')

    def chooser_callback(self, shared_file_list):
        ss = SharedStorage()
        for shared_file in shared_file_list:
            path = ss.copy_from_shared(shared_file)
            if path:
                self.handle_image(path)

    @mainthread
    def handle_image(self,image_path):
        try:
            img = Image.open(image_path)
            output_buffer = BytesIO()

            if "camera_tmp" in image_path:
                if img.width > img.height:
                    img = img.rotate(270,expand=True)

                frame_height = img.height/8
                frame_width = img.width/6*4

                start_x = (img.width/2) - (frame_width/2)
                start_y = img.height/3

                end_x = start_x + frame_width
                end_y = start_y + frame_height

                img = img.crop((start_x,start_y,end_x,end_y))

            img.save(output_buffer, format='PNG' if image_path.split(".")[-1] == "png" else "JPEG",quality=20,optimize=True)
            base64_str = base64.b64encode(output_buffer.getvalue())
            self.send_b64(base64_str)

        except Exception as e:
            err = f"\n\n{e}" if self.settings["enable_debug_mode"]['mode'] == True else ""
            popup = MDDialog(title='Ошибка',text=f'Не удалось открыть изображение{err}',buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color="#02714C",on_release=lambda *args:popup.dismiss())])
            popup.open()  
        
    def choose(self):
        if platform == "android":
            self.chooser.choose_content('image/*', multiple = False)
        else:pass

    def load_history(self):
        history_layout = self.root.ids.history_layout
        history_layout.clear_widgets()
        try:
            history = dict(self.history)
            if self.history.count() != 0:
                self.root.ids.history_clear_btn.disabled = False
                history_sw = MDList()
                self.root.ids.history_layout.add_widget(history_sw)

                for elem in reversed(history):
                    equ_type = history[elem]['equ_type']
                    equ_text = history[elem]['equation']
                    f = lambda s:self.send_equation(s.secondary_text,from_history=True)
                    history_sw.add_widget(TwoLineListItem(text=equ_type,secondary_text=equ_text,on_release=f))
            else:
                self.root.ids.history_clear_btn.disabled = True
                history_layout.add_widget(MDLabel(text="Пусто",halign="center",font_style="H5"))
        except Exception as e:
            Logger.error(f"History exception: {e}")
            self.history.clear()
            self.set_screen("sc_history")

    def setup(self):
        try:
            for elem_id in self.settings.keys():
                self.root.ids[elem_id].active = self.settings[elem_id]['mode']
        except Exception as e:
            Logger.error(f"Setup error: {e}")
            self.set_settings(reset=True)

    def set_settings(self,reset=False):
        if reset == True:
            default_history = json.load(open('data/settings.json'))
            self.settings.clear()
            Logger.info("Settings: Clear settings")
            for elem in default_history:
                self.settings[elem] = default_history[elem]

    def key_handler(self, window, keycode,*args):
        manager = self.root.ids.sm
        if keycode in [27, 1001]:
            if manager.current != 'sc_photo':
                self.set_screen(self.last_screen)
            return True
        return False
    
    def photo(self):
        self.root.ids.preview.capture_photo(location="private",subdir="camera_tmp")

    def handle_camera(self):
        if self.root.ids.preview.camera_connected == True:
            flashlight_modes = {"on":"flash","off":"flash-off"}
            state = self.root.ids.preview.flash(self.flashlight_mode)
            self.root.ids.flashlight_btn.icon = flashlight_modes[state]

    def switch_flashlight_mode(self):
        flashlight_modes = {"on":"flash","off":"flash-off"}
        self.flashlight_mode = "on" if self.flashlight_mode == "off" else "off"
        icon = self.root.ids.preview.flash(self.flashlight_mode)
        self.root.ids.flashlight_btn.icon = flashlight_modes[icon]

    def open_browser(self,url):
        webbrowser.open(url)

    def copy_content(self,text):
        Clipboard.copy(text)

    def clear_cache(self,paths):
        for path_name in paths:
            if os.path.exists(path_name):
                shutil.rmtree(path_name, ignore_errors=True)
        
        toast("Кеш очищен")

    def set_screen(self,screen_name,*screen_title,root_=False):
        if root_ == False:
            if self.root.current == "main_sc":
                self.last_screen = self.root.ids['sm'].current
                self.root.ids['sm'].current = screen_name
                if screen_title:self.root.ids['tb'].title = screen_title[0]
                self.root.ids['nav_drawer'].set_state("closed")
                self.root.ids.textarea.ids.text_field.focus = False
        else:
            self.root.current = screen_name
    
    def edit_textfield(self,text,move_cursor=0):
        textfield = self.root.ids.textarea.ids.text_field
        self.root.ids.textarea.ids.text_field.last_edit = self.root.ids.textarea.ids.text_field.text
        cursor_index = int(textfield.cursor[0])
        textfield.text = textfield.text[:textfield.cursor[0]] + text + textfield.text[textfield.cursor[0]:]
        textfield.cursor = (cursor_index+len(text)-move_cursor,0)
    
    def undo_textfield(self):
        self.root.ids.textarea.ids.text_field.text = self.root.ids.textarea.ids.text_field.last_edit

    def delete_textfield(self):
        self.root.ids.textarea.ids.text_field.last_edit = self.root.ids.textarea.ids.text_field.text
        textfield = self.root.ids.textarea.ids.text_field
        cursor_index = int(textfield.cursor[0])
        if cursor_index > 0:
            textfield.text = textfield.text[:(cursor_index-1)] + textfield.text[cursor_index:]
        textfield.cursor = (cursor_index-1,0)

    def move_cursor(self,direction):
        cursor = self.root.ids.textarea.ids.text_field.cursor
        max_index = len(self.root.ids.textarea.ids.text_field.text)+1

        if direction == "right":
            cursor_pos = cursor[0]+1 if cursor[0]+1 < max_index else 0

        if direction == "left":
            cursor_pos = cursor[0]-1 if cursor[0]-1 >= 0 else max_index

        self.root.ids.textarea.ids.text_field.cursor = (cursor_pos,0)

    def set_kb(self,kb_name):
        kb_manager = self.root.ids.kb_manager
        screens_list = ["main_kb","trigonometry_kb","letters_kb"]
        if kb_name == "next":
            if screens_list.index(kb_manager.current)+1 < len(screens_list):
                next_screen = screens_list[screens_list.index(kb_manager.current)+1]

            elif screens_list.index(kb_manager.current)+1 == len(screens_list):
                next_screen = screens_list[0]

            kb_manager.current = next_screen

        else:kb_manager.current = kb_name

    def send_equation(self,*args,from_history=False):
        equation = args[0] if args else self.root.ids.textarea.ids.text_field.text

        if equation != "":
            self.root.ids.textarea.ids.text_field.focus = False

            loading_popup = MDDialog(title='Загрузка',text='Ожидаем ответ от сервера...',auto_dismiss=False)
            loading_popup.open()

            params = urllib.parse.urlencode({'src':equation})

            def success(req, result):
                loading_popup.dismiss()
                status_code = result['status_code']

                if status_code == 0:
                    gamma_result = result['message']
                    self.root.ids.gl.clear_widgets()
                    gamma_output = str(gamma_result[0]['output']) if 'output' in gamma_result[0].keys() else ""
                    problem_main = ''.join(gamma_output.split(" "))

                    for card in gamma_result:
                        valid_card = ("title" in card.keys() and card['title'] != "") and ("output" in card.keys() and card['output'] != "")
                        contains_plot = 'card' in list(card.keys()) and card['card'] == "plot"
                        #contains_latex = 'pre_output' in list(card.keys()) and card['pre_output'] != card['var'] and card['pre_output'] != "\\mathtt{\\text{}}"
                        
                        kv_card = MDCard(orientation="vertical",pos_hint={"top":1},md_bg_color="#039866",padding=[30,15,30,15],size_hint_y=None,spacing=10)
                        title_label = MDLabel(text=f"{card['title']}:",adaptive_height=True,theme_text_color="Custom",text_color="white",font_style="H6")
                        kv_card.add_widget(title_label)

                        if contains_plot == True:
                            plot_url = self.config_["plotting_url"]+"?src="+problem_main
                            image_widget = FitImage(source=plot_url,pos_hint={"center_x":.5},size_hint=(1.3,3.5))
                            kv_card.height = dp(kv_card.height*1.4)+dp(image_widget.height*1.4)
                            kv_card.add_widget(image_widget)

                        #elif contains_latex == True:
                        #    plot_url = self.config_["latex_url"].format(f"{card['pre_output']} = {card['output']}".replace(" ",""))
                        #    image_widget = FitImage(source=plot_url,pos_hint={"center_x":.5})
                        #    kv_card.height = image_widget.height
                        #    kv_card.add_widget(image_widget)

                        else:
                            kv_card.adaptive_height = True
                            result_text = card['output'] if 'output' in card.keys() else ""
                            output_label = MDLabel(text=result_text,adaptive_height=True,theme_text_color="Custom",text_color="white")
                            kv_card.add_widget(output_label)

                        if valid_card or contains_plot:
                            self.root.ids.gl.add_widget(kv_card)

                    self.root.ids.gl.problem_main = problem_main
                    self.root.ids.gl.problem_input = equation
                    self.root.ids.gl.gamma_url = f"https://sympygamma.com/input/?i={gamma_output.replace(' ','')}"
                    
                    if self.settings['enable_debug_mode']['mode'] == True:
                        self.root.ids.gl.add_widget(MDRectangleFlatButton(text="Скопировать json",on_release=lambda f:self.copy_content(str(gamma_result))))
                        self.root.ids.gl.add_widget(MDRectangleFlatButton(text="Открыть в Sympy Gamma",on_release=lambda f:self.open_browser(self.root.ids.gl.gamma_url)))
                    
                    self.set_screen("sc_solve")
                    
                    if from_history == False:
                        self.history[self.history.count()+1] = {"equ_type":gamma_result[0]['title'],"equation":equation}

                else:
                    err = f"\n\n{result}" if self.settings["enable_debug_mode"]['mode'] == True else ""
                    popup = MDDialog(title='Ошибка',text=f'Не удалось решить задачу, проверьте правильность введённых данных{err}',buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color="#02714C",on_release=lambda *args:popup.dismiss())])
                    popup.open()   

            def error(req, result):
                loading_popup.dismiss()
                result = str(result).replace("\n","")
                err = f"\n\n{result}" if self.settings["enable_debug_mode"]['mode'] == True else ""
                popup = MDDialog(title='Ошибка',text=f'Не удаётся получить ответ от сервера,\nпроверьте подключение к интернету{err}',buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color="#02714C",on_release=lambda *args:popup.dismiss())])
                popup.open()
                
            if "math_solve_url" in self.config_.keys():
                req = UrlRequest(self.config_["math_solve_url"],on_success=success,on_failure=error,on_error=error,req_body=params,req_headers={'Content-type': 'application/x-www-form-urlencoded','Accept': 'text/plain'},ca_file=certifi.where(),verify=True,method='POST')
        else:
            self.root.ids.textarea.ids.text_field.error = True

    def get_logs(self):
        logs_path = shutil.make_archive('logs', 'zip', root_dir='.kivy/logs')
        ss = SharedStorage()
        ss.copy_to_shared(logs_path,filepath='/logs')
        toast(f"Логи выгружены: Documents/MathCamera/logs")

    def send_b64(self,b64):
        loading_popup = MDDialog(title='Загрузка',text='Ожидаем ответ от сервера...',auto_dismiss=False)
        loading_popup.open()

        params = urllib.parse.urlencode({'src':b64})
        def success(req, result):
            loading_popup.dismiss()
            status_code = result['status_code']
            result = result["message"]

            try:
                if status_code == 0:
                    if result == "":
                        popup = MDDialog(title="Ошибка",text="Не удалось распознать текст на фото",buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color="#02714C",on_release=lambda *args:popup.dismiss())])
                        popup.open()
                    
                    else:
                        self.set_screen("sc_text")
                        self.root.ids.textarea.ids.text_field.text = result
                
                else:
                    popup = MDDialog(title="Ошибка",text='{result}\nStatus code: {st_code}'.format(result=result,st_code=status_code),buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color="#02714C",on_release=lambda *args:popup.dismiss())])
                    popup.open()
                    
            except:
                popup = MDDialog(title="Ошибка",text="Не удалось распознать текст на фото",buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color="#02714C",on_release=lambda *args:popup.dismiss())])
                popup.open()   

        def error(req, result):
            loading_popup.dismiss()
            result = str(result).replace("\n","")
            err = f"\n\n{result}" if self.settings["enable_debug_mode"]['mode'] == True else ""
            popup = MDDialog(title='Ошибка',text=f'Не удаётся получить ответ от сервера,\nпроверьте подключение к интернету{err}',buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color="#02714C",on_release=lambda *args:popup.dismiss())])
            popup.open()

        if "ocr_url" in self.config_.keys():
            ocr_url = self.config_["debug_server_url"] if self.settings["enable_test_server"]['mode'] == True else self.config_["ocr_url"]
            req = UrlRequest(ocr_url,on_success=success,on_failure=error,on_error=error,req_body=params,req_headers={'Content-type': 'application/x-www-form-urlencoded','Accept': 'text/plain'},ca_file=certifi.where(),verify=True,method='POST')
            
if __name__ == "__main__":
    MathCamera().run()