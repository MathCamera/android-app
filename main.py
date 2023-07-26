__version__ = "0.7.5"

from kivy.lang import Builder
from kivy.clock import Clock,mainthread
from kivy.utils import platform
from kivy.metrics import dp
from kivy.network.urlrequest import UrlRequest
from kivy.core.window import Window
from kivy.storage.jsonstore import JsonStore

from kivymd.app import MDApp
from kivymd.toast import toast
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.list import TwoLineListItem,MDList
from kivymd.uix.label import MDLabel

from modules.android_api import check_camera_permission,check_request_camera_permission,set_orientation
from modules.plotting import render_plot
from camera4kivy import Preview

import base64,os,certifi,urllib.parse,json,webbrowser,shutil
from packaging import version
from PIL import Image
from io import BytesIO

if platform == "android":
    from androidstorage4kivy import Chooser,SharedStorage
else:
    Window.size = (360,600)

class MathCamera(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.version_ = __version__

        self.data_dir = os.path.join("..","user_data")
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            os.replace("data/settings.json",os.path.join(self.data_dir,"settings.json"))
            #Действия при первом запуске после первой установки

        self.history = JsonStore(os.path.join(self.data_dir,'history.json'))
        self.settings = json.load(open(os.path.join(self.data_dir,'settings.json')))
            
        self.config_ = json.load(open('data/config.json'))
        self.theme_cls.colors = json.load(open('data/themes.json'))

        self.theme_cls.material_style = "M2"
        self.main_colors = ["#02714C","#039866"]

        self.last_screen,self.solver_type = None,None
        self.flashlight_modes = {"on":"flash","auto":"flash-auto","off":"flash-off"}
        self.menu_items = {"digital":"Решить пример",
                           "equation":"Решить уравнение",
                           "system":"Решить систему уравнений",
                           "simplify":"Упростить выражение",
                           "inequality":"Решить неравенство"}

    def build(self):
        self.theme_cls.theme_style = "Dark" if self.settings["dark_theme"] == True else "Light"
        if platform == "android":
            self.chooser = Chooser(self.chooser_callback)
        
        return Builder.load_file('data/md.kv')
    
    def update_config(self):
        def success(req,result):
            result = json.loads(result)
            self.config_["math_solve_url"] = result["math_solve_url"]
            self.config_["ocr_url"] = result["ocr_url"]
        
            if version.parse(__version__) < version.parse(result["latest_version"]):
                download_url = result["download_url"]
                popup = MDDialog(title='Доступно новое обновление',text=f'Вы хотите обновить приложение?',buttons=[MDFlatButton(text="Обновить",theme_text_color="Custom",text_color=self.main_colors[0],on_release=lambda *args:launch_update()),MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color=self.main_colors[0],on_release=lambda *args:popup.dismiss())])
                popup.open()  

                def launch_update():
                    webbrowser.open(download_url)
            
            with open("data/config.json","w") as file:
                file.write(json.dumps(self.config_))           

        req = UrlRequest(self.config_['config_url'],on_success=success,req_headers={'Content-type': 'application/x-www-form-urlencoded','Accept': 'text/plain'},ca_file=certifi.where(),verify=True,method='GET')

    def on_start(self):
        check_request_camera_permission()
        set_orientation()
        Window.bind(on_keyboard=self.key_handler)
        self.update_config()
        Clock.schedule_once(self.connect_camera)

    def on_stop(self):
        self.root.ids.preview.disconnect_camera()

    def connect_camera(self,dt):
        self.root.ids.preview.connect_camera(enable_video = False,filepath_callback=self.handle_choose)

    def chooser_callback(self, shared_file_list):
        ss = SharedStorage()
        for shared_file in shared_file_list:
            path = ss.copy_from_shared(shared_file)
            if path:
                self.handle_choose(path)

    @mainthread
    def handle_choose(self,image_path):
        try:
            img = Image.open(image_path)
            output_buffer = BytesIO()
            img.save(output_buffer, format='PNG' if image_path.split(".")[-1] == "png" else "JPEG")
            base64_str = base64.b64encode(output_buffer.getvalue())
            self.send_b64(base64_str)
        except Exception as e:
            err = f"\n\n{e}" if self.settings["debug_mode"] == True else ""
            popup = MDDialog(title='Ошибка',text=f'Не удалось открыть изображение{err}',buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color=self.main_colors[0],on_release=lambda *args:popup.dismiss())])
            popup.open()  
        
    def choose(self):
        if platform == "android":
            self.chooser.choose_content('image/*', multiple = False)
        else:pass

    def set_kb(self,kb_name):
        kb_manager = self.root.ids.kb_manager
        screens_list = ["main_kb","letters_kb","functions_kb"]
        if kb_name == "next":
            if screens_list.index(kb_manager.current)+1 < len(screens_list):
                next_screen = screens_list[screens_list.index(kb_manager.current)+1]

            elif screens_list.index(kb_manager.current)+1 == len(screens_list):
                next_screen = screens_list[0]

            kb_manager.current = next_screen

        else:
            kb_manager.current = kb_name

    def load_history(self):
        history_layout = self.root.ids.history_layout
        history_layout.clear_widgets()

        if len(self.history) != 0:
            self.root.ids.history_clear_btn.disabled = False
            history_sw = MDList()
            self.root.ids.history_layout.add_widget(history_sw)
            for elem in self.history:
                equ_type = self.history[elem]['equ_type']
                equ_text = elem
                f = lambda s:self.send_equation(s.secondary_text,list(self.menu_items.keys())[list(self.menu_items.values()).index(s.text)],from_history=True)
                history_sw.add_widget(TwoLineListItem(text=self.menu_items[equ_type],secondary_text=equ_text,on_release=f))
        else:
            self.root.ids.history_clear_btn.disabled = True
            history_layout.add_widget(MDLabel(text="Пусто",halign="center",font_style="H5"))

    def clear_history(self):
        for elem in self.history:
            self.history.delete(elem)

    def clear_cache(self):
        paths = ['mpl_tmp','camera_tmp']
        for path_name in paths:
            if os.path.exists(path_name):
                shutil.rmtree(path_name, ignore_errors=True)
        
        toast("Кеш очищен")

    def setup(self):
        ids = self.root.ids
        settings = self.settings

        for elem_id in settings.keys():
            if elem_id != "flashlight":
                ids[elem_id].active = settings[elem_id]

        ids["enable_flashlight"].active = True if settings['flashlight'] == "on" or settings['flashlight'] == "auto" else False
        ids["auto_flashlight"].disabled = True if settings["flashlight"] == "off" else False
        ids["auto_flashlight"].active = True if settings["flashlight"] == "auto" else False

    def handle_switch(self,type,state):
        if type == "flashlight":
            if state == "off":
                self.root.ids["auto_flashlight"].active = False
                self.root.ids["auto_flashlight"].disabled = True
            elif state == "on":
                self.root.ids["auto_flashlight"].disabled = False

        if type == "dark_theme":
            self.theme_cls.theme_style = "Dark" if state == True else "Light"

        self.settings[type] = state

        with open(os.path.join(self.data_dir,'settings.json'),"w") as file:
            file.write(json.dumps(self.settings))

    def key_handler(self, window, keycode,*args):
        manager = self.root.ids["sm"]
        if keycode in [27, 1001]:
            if manager.current != 'sc_home':
                self.set_screen(self.last_screen)
            return True
        return False
    
    def photo(self):
        try:
            self.root.ids.preview.capture_photo(location="private",subdir="camera_tmp")
        except Exception as e:
            if check_camera_permission() == True:
                err = e
                err = f"\n\n{e}" if self.settings["debug_mode"] == True else ""
                popup = MDDialog(title='Ошибка',text=f'Не удалось подключиться к камере. Перезагрузите приложение {err}',buttons=[MDFlatButton(text="Перезагрузить",theme_text_color="Custom",text_color=self.main_colors[0],on_release=lambda *args:self.stop())])
                popup.open()
            else:
                self.perm_dialog = MDDialog(
                    text="Не удалось подключиться к камере, поскольку приложению не разрешён доступ к ней. Разрешить доступ к камере?",
                    buttons=[
                        MDFlatButton(
                            text="Отмена",
                            theme_text_color="Custom",
                            text_color=self.main_colors[0],
                            on_release=lambda *args:self.perm_dialog.dismiss(),
                        ),
                        MDFlatButton(
                            text="Разрешить",
                            theme_text_color="Custom",
                            text_color=self.main_colors[0],
                            on_release=lambda *args:self.request_camera_perm,
                        ),
                    ],
                )
                self.perm_dialog.open()

    def request_camera_perm(self,*args):
        try:
            check_request_camera_permission()
            self.perm_dialog.dismiss()
        except:pass

    def handle_camera(self):
        flashlight = self.settings["flashlight"]
        state = self.root.ids.preview.flash(flashlight)
        self.root.ids.flashlight_btn.icon = self.flashlight_modes[state]

    def switch_flashlight_mode(self):
        icon = self.root.ids.preview.flash()
        self.root.ids.flashlight_btn.icon = self.flashlight_modes[icon]
        self.settings['flashlight'] = icon

        with open(os.path.join(self.data_dir,'settings.json'),"w") as file:
            file.write(json.dumps(self.settings))

    def open_browser(self,url):
        webbrowser.open(url)

    def set_screen(self,screen_name,*screen_title):
        if self.root.current == "main_sc":
            self.last_screen = self.root.ids['sm'].current
            
            self.root.ids['sm'].current = screen_name

            if screen_title:
                self.root.ids['tb'].title = screen_title[0]

            self.root.ids['nav_drawer'].set_state("closed")

            self.root.ids.textarea.ids.text_field.focus = False

        #Window.clearcolor = (0,0,0,0) if screen_name == "sc_photo" else (1,1,1,1)
    
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

    def on_text_screen(self):
        self.root.ids.textarea.ids.text_field._hide_cut_copy_paste()
        menu_items = [
            {
                "text": i,
                "on_release": lambda x=i: set_item(x),
            } for i in self.menu_items.values()]

        self.menu = MDDropdownMenu(
            caller=self.root.ids.drop_item,
            items=menu_items,
            position="bottom",
            border_margin=24,
        )
        self.menu.bind()

        def set_item(text_item):
            self.root.ids.drop_item.set_item(text_item)
            self.menu.dismiss()
            self.solver_type = list(self.menu_items.keys())[list(self.menu_items.values()).index(text_item)]

    def send_equation(self,*args,from_history=False):
        if args:
            equation = args[0]
            solver_type = args[1]
        else:
            equation = self.root.ids.textarea.ids.text_field.text
            solver_type = self.solver_type

        if equation != "" and solver_type!= None:
            self.root.ids.textarea.ids.text_field.focus = False

            loading_popup = MDDialog(title='Загружаем данные',text='Загрузка...',auto_dismiss=False)
            loading_popup.open()

            params = urllib.parse.urlencode({'src':equation,"type":solver_type})

            def success(req, result):
                loading_popup.dismiss()
                status_code = result['status_code']
                if status_code == 0:
                    
                    if "plot" in result.keys():
                        plot_filename = render_plot(result['plot'])
                        if plot_filename != None:
                            self.root.ids["plot_img"].source = plot_filename
                            self.root.ids['plot_card'].visible = True
                            self.root.ids.gl_sw.do_scroll_y = True

                        else:
                            self.root.ids['plot_card'].visible = False
                            self.root.ids.gl_sw.do_scroll_y = False
                    else:
                        self.root.ids['plot_card'].visible = False
                        self.root.ids.gl_sw.do_scroll_y = False

                    self.root.ids["equation_label"].text = equation
                    self.root.ids["solution_label"].text = result["message"]

                    self.set_screen("sc_solve")
                    self.root.ids.gl_sw.scroll_y=1
                    
                    self.root.ids["equ_type_label"].text = self.menu_items[solver_type]

                    if from_history == False:
                        self.history[equation] = {"equ_type":solver_type}
    
                else:
                    err = f"\n\n{result}" if self.settings["debug_mode"] == True else ""
                    popup = MDDialog(title='Ошибка',text=f'Не удалось решить задачу, проверьте правильность введённых данных{err}',buttons=[MDFlatButton(text="Помощь",theme_text_color="Custom",text_color=self.main_colors[0],on_release=lambda *args:webbrowser.open(self.config_["help_url"]+solver_type)),MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color=self.main_colors[0],on_release=lambda *args:popup.dismiss())])
                    popup.open()   

            def error(req, result):
                loading_popup.dismiss()
                result = str(result).replace("\n","")
                err = f"\n\n{result}" if self.settings["debug_mode"] == True else ""
                popup = MDDialog(title='Ошибка',text=f'Не удаётся получить ответ от сервера,\nпроверьте подключение к интернету{err}',buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color=self.main_colors[0],on_release=lambda *args:popup.dismiss())])
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
        loading_popup = MDDialog(title='Загружаем данные',text='Загрузка...',auto_dismiss=False)
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
                        popup = MDDialog(title="Ошибка",text="Не удалось распознать текст на фото",buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color=self.main_colors[0],on_release=lambda *args:popup.dismiss())])
                        popup.open()
                    
                    else:
                        self.set_screen("sc_text")

                        if len(result) > 50: result = result[-50:]
                        self.root.ids.textarea.ids.text_field.text = result
                        self.root.ids.textarea.ids.text_field.focus=True
                
                else:
                    popup = MDDialog(title="Ошибка",text='{result}\nStatus code: {st_code}'.format(result=result,st_code=status_code),buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color=self.main_colors[0],on_release=lambda *args:popup.dismiss())])
                    popup.open()
                    
            except:
                popup = MDDialog(title="Ошибка",text="Не удалось распознать текст на фото",buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color=self.main_colors[0],on_release=lambda *args:popup.dismiss())])
                popup.open()   

        def error(req, result):
            loading_popup.dismiss()
            result = str(result).replace("\n","")
            err = f"\n\n{result}" if self.settings["debug_mode"] == True else ""
            popup = MDDialog(title='Ошибка',text=f'Не удаётся получить ответ от сервера,\nпроверьте подключение к интернету{err}',buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color=self.main_colors[0],on_release=lambda *args:popup.dismiss())])
            popup.open()
        
        req = UrlRequest(self.config_["ocr_url"],on_success=success,on_failure=error,on_error=error,req_body=params,req_headers={'Content-type': 'application/x-www-form-urlencoded','Accept': 'text/plain'},ca_file=certifi.where(),verify=True,method='POST')

if __name__ == "__main__":
    MathCamera().run()