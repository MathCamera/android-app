__version__ = "0.8.0"

from kivy.lang import Builder
from kivy.clock import mainthread
from kivy.utils import platform
from kivy.metrics import dp
from kivy.network.urlrequest import UrlRequest
from kivy.core.window import Window
from kivy.core.clipboard import Clipboard
from kivy.storage.jsonstore import JsonStore
from kivy.loader import Loader
Loader.loading_image = "media/loader.png"

from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton,MDRectangleFlatButton
from kivymd.uix.list import TwoLineListItem,MDList
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.fitimage import FitImage

from modules.android_api import request_camera_permission,set_orientation
from modules.xcamera import *

import base64,os,certifi,urllib.parse,json,webbrowser,shutil
from PIL import Image
from io import BytesIO

if platform == "android":
    from androidstorage4kivy import Chooser,SharedStorage
    from kvdroid.tools import change_statusbar_color,toast
    from kvdroid.tools.darkmode import dark_mode
    change_statusbar_color("#02714C", "white")
else:
    Window.size = (360,600)

class MathCamera(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.version_ = __version__
        self.data_dir = os.path.join("..","user_data")
        self.theme_cls.colors = json.load(open('data/themes.json'))
        self.theme_cls.material_style = "M2"
        self.main_colors = ["#02714C","#039866"]
        self.last_screen,self.flashlight_mode,self.config_ = None,"off",{'config_url':"https://mathcamera-api.vercel.app/config"}

    def build(self):        
        return Builder.load_file('data/md.kv')  
    
    def on_start(self):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            shutil.copyfile("data/settings.json",os.path.join(self.data_dir,"settings.json"))

        self.settings = json.load(open(os.path.join(self.data_dir,'settings.json')))
        self.history = JsonStore(os.path.join(self.data_dir,'history.json'))

        if json.load(open('data/settings.json')).keys() != self.settings.keys():
            self.set_settings(reset=True)

        request_camera_permission()
        set_orientation()
        self.update_config()
        Window.bind(on_keyboard=self.key_handler)
        self.root.ids.preview.connect_camera(enable_video = False,filepath_callback=self.handle_image,enable_analyze_pixels=True)
        
        if platform == "android":
            self.theme_cls.theme_style = "Dark" if dark_mode() == True else "Light"
            self.chooser = Chooser(self.chooser_callback)

    def on_stop(self):
        self.root.ids.preview.disconnect_camera()
    
    def set_settings(self,reset=False):
        if reset == True:
            self.settings = json.load(open('data/settings.json'))

        with open(os.path.join(self.data_dir,'settings.json'),"w") as file:
            file.write(json.dumps(self.settings))

    def handle_switch(self,type,state):
        self.settings[type] = state
        self.set_settings()
    
    def update_config(self):
        def success(req,result):
            for elem in result.keys():
                self.config_[elem] = result[elem]
        
            if __version__ != result["latest_version"]:
                popup = MDDialog(title='Доступно новое обновление',text=f'Вы хотите обновить приложение?',buttons=[MDFlatButton(text="Обновить",theme_text_color="Custom",text_color="#02714C",on_release=lambda *args:launch_update()),MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color="#02714C",on_release=lambda *args:popup.dismiss())])
                popup.open()  

                def launch_update():
                    webbrowser.open(result["download_url"])  

        def error(req, result):
            result = str(result).replace("\n","")
            err = f"\n\n{result}" if self.settings["debug_mode"] == True else ""
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
            img.save(output_buffer, format='PNG' if image_path.split(".")[-1] == "png" else "JPEG",quality=20,optimize=True)
            base64_str = base64.b64encode(output_buffer.getvalue())
            self.send_b64(base64_str)

        except Exception as e:
            err = f"\n\n{e}" if self.settings["debug_mode"] == True else ""
            popup = MDDialog(title='Ошибка',text=f'Не удалось открыть изображение{err}',buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color="#02714C",on_release=lambda *args:popup.dismiss())])
            popup.open()  
        
    def choose(self):
        if platform == "android":
            self.chooser.choose_content('image/*', multiple = False)
        else:pass

    def set_kb(self,kb_name):
        kb_manager = self.root.ids.kb_manager
        screens_list = ["main_kb","trigonometry_kb","letters_kb","functions_kb"]
        if kb_name == "next":
            if screens_list.index(kb_manager.current)+1 < len(screens_list):
                next_screen = screens_list[screens_list.index(kb_manager.current)+1]

            elif screens_list.index(kb_manager.current)+1 == len(screens_list):
                next_screen = screens_list[0]

            kb_manager.current = next_screen

        else:kb_manager.current = kb_name

    def load_history(self):
        history_layout = self.root.ids.history_layout
        history_layout.clear_widgets()
        try:
            if len(self.history) != 0:
                self.root.ids.history_clear_btn.disabled = False
                history_sw = MDList()
                self.root.ids.history_layout.add_widget(history_sw)

                for elem in self.history:
                    equ_type = self.history[elem]['equ_type']
                    equ_text = elem
                    f = lambda s:self.send_equation(s.secondary_text,from_history=True)
                    history_sw.add_widget(TwoLineListItem(text=equ_type,secondary_text=equ_text,on_release=f))
            else:
                self.root.ids.history_clear_btn.disabled = True
                history_layout.add_widget(MDLabel(text="Пусто",halign="center",font_style="H5"))
        except:
            self.clear_history()
            self.set_screen("sc_history")

    def clear_history(self):
        for elem in self.history:
            self.history.delete(elem)

    def setup(self):
        ids = self.root.ids
        settings = self.settings

        for elem_id in settings.keys():
            ids[elem_id].active = settings[elem_id]

    def key_handler(self, window, keycode,*args):
        manager = self.root.ids["sm"]
        if keycode in [27, 1001]:
            if manager.current != 'sc_home':
                self.set_screen(self.last_screen)
            return True
        return False
    
    def photo(self):
        self.root.ids.preview.capture_photo(location="private",subdir="camera_tmp")

    def handle_camera(self):
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

    def set_screen(self,screen_name,*screen_title):
        if self.root.current == "main_sc":
            self.last_screen = self.root.ids['sm'].current
            self.root.ids['sm'].current = screen_name
            if screen_title:self.root.ids['tb'].title = screen_title[0]
            self.root.ids['nav_drawer'].set_state("closed")
            self.root.ids.textarea.ids.text_field.focus = False
    
    def edit_textfield(self,text,move_cursor=0):
        textfield = self.root.ids.textarea.ids.text_field
        cursor_index = int(textfield.cursor[0])
        textfield.text = textfield.text[:textfield.cursor[0]] + text + textfield.text[textfield.cursor[0]:]
        textfield.cursor = (cursor_index+len(text)-move_cursor,0)

    def delete_textfield(self):
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

                    for card in gamma_result:
                        contains_plot = 'card' in list(card.keys()) and card['card'] == "plot"
                        #contains_latex = 'pre_output' in list(card.keys()) and card['pre_output'] != card['var'] and card['pre_output'] != "\\mathtt{\\text{}}"
                        
                        kv_card = MDCard(orientation="vertical",pos_hint={"top":1},md_bg_color="#039866",padding=[30,15,30,15],size_hint_y=None,spacing=10)
                        title_label = MDLabel(text=f"{card['title']}:",adaptive_height=True,theme_text_color="Custom",text_color="white",font_style="H6")
                        kv_card.add_widget(title_label)

                        if contains_plot == True:
                            plot_url = self.config_["plotting_url"].format(str(card['input']).replace(" ",""))
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
                            result_text = card['output']
                            output_label = MDLabel(text=result_text,adaptive_height=True,theme_text_color="Custom",text_color="white")
                            kv_card.add_widget(output_label)

                        self.root.ids.gl.add_widget(kv_card)
                    
                    if self.settings['debug_mode'] == True:
                        self.root.ids.gl.add_widget(MDRectangleFlatButton(text="Скопировать json",on_release=lambda f:self.copy_content(str(gamma_result))))
                        self.root.ids.gl.add_widget(MDRectangleFlatButton(text="Открыть в Sympy Gamma",on_release=lambda f:self.open_browser(f"https://sympygamma.com/input/?i={gamma_result[0]['output']}")))
                    
                    self.set_screen("sc_solve")
                    
                    if from_history == False:
                        self.history[equation] = {"equ_type":gamma_result[0]['title']}

                else:
                    err = f"\n\n{result}" if self.settings["debug_mode"] == True else ""
                    popup = MDDialog(title='Ошибка',text=f'Не удалось решить задачу, проверьте правильность введённых данных{err}',buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color="#02714C",on_release=lambda *args:popup.dismiss())])
                    popup.open()   

            def error(req, result):
                loading_popup.dismiss()
                result = str(result).replace("\n","")
                err = f"\n\n{result}" if self.settings["debug_mode"] == True else ""
                popup = MDDialog(title='Ошибка',text=f'Не удаётся получить ответ от сервера,\nпроверьте подключение к интернету{err}',buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color="#02714C",on_release=lambda *args:popup.dismiss())])
                popup.open()
                
            req = UrlRequest(self.config_["math_solve_url"],on_success=success,on_failure=error,on_error=error,req_body=params,req_headers={'Content-type': 'application/x-www-form-urlencoded','Accept': 'text/plain'},ca_file=certifi.where(),verify=True,method='POST')
            
        else:
            self.root.ids.textarea.ids.text_field.error = True

    def get_logs(self):
        logs_path = '.kivy/logs'
        r = os.listdir(logs_path)
        last_log = len(r)-2

        f = open(f"{logs_path}/{r[last_log]}", 'r')
        file_contents = f.read()
        f.close()
        return file_contents

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
                    result = " ".join(str(result).split())

                    if result == "":
                        popup = MDDialog(title="Ошибка",text="Не удалось распознать текст на фото",buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color="#02714C",on_release=lambda *args:popup.dismiss())])
                        popup.open()
                    
                    else:
                        self.set_screen("sc_text")
                        if len(result) > 50: result = result[-50:]
                        self.root.ids.textarea.ids.text_field.text = result
                        self.root.ids.textarea.ids.text_field.focus=True
                
                else:
                    popup = MDDialog(title="Ошибка",text='{result}\nStatus code: {st_code}'.format(result=result,st_code=status_code),buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color="#02714C",on_release=lambda *args:popup.dismiss())])
                    popup.open()
                    
            except:
                popup = MDDialog(title="Ошибка",text="Не удалось распознать текст на фото",buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color="#02714C",on_release=lambda *args:popup.dismiss())])
                popup.open()   

        def error(req, result):
            loading_popup.dismiss()
            result = str(result).replace("\n","")
            err = f"\n\n{result}" if self.settings["debug_mode"] == True else ""
            popup = MDDialog(title='Ошибка',text=f'Не удаётся получить ответ от сервера,\nпроверьте подключение к интернету{err}',buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color="#02714C",on_release=lambda *args:popup.dismiss())])
            popup.open()
        
        req = UrlRequest(self.config_["ocr_url"],on_success=success,on_failure=error,on_error=error,req_body=params,req_headers={'Content-type': 'application/x-www-form-urlencoded','Accept': 'text/plain'},ca_file=certifi.where(),verify=True,method='POST')

if __name__ == "__main__":
    MathCamera().run()