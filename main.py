__version__ = "0.6.5"

from kivy.lang import Builder
from kivy.clock import mainthread
from kivy.utils import platform
from kivy.metrics import dp
from kivy.network.urlrequest import UrlRequest
from kivy.core.window import Window

from kivymd.app import MDApp
from kivymd.toast import toast
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.list import TwoLineListItem

from modules.xcamera.xcamera import check_camera_permission,check_request_camera_permission
from modules.plotting import render_plot

import base64,os,certifi,urllib.parse,json,webbrowser,shutil
from packaging import version
from PIL import Image
from io import BytesIO

if platform == "android":
    from androidstorage4kivy import Chooser,SharedStorage
    from modules.android_api import send_to_downloads
else:
    Window.size = (360,600)

class MathCamera(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config_ = json.load(open('data/config.json'))
        self.settings = json.load(open('data/settings.json'))
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
        
        self.screen_names = {"sc_home":"Главная",
                        "sc_photo":"Сканировать",
                        "sc_text":"Калькулятор",
                        "sc_solve":"Решение",
                        "sc_history":"История",
                        "sc_logs":"Логи",
                        "sc_settings":"Настройки"}

    def build(self):
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
                    self.root.current = "update_sc"
                    popup.dismiss()
                    self.download_content(download_url)
            
            with open("data/config.json","w") as file:
                file.write(json.dumps(self.config_))            

        req = UrlRequest(self.config_['config_url'],on_success=success,req_headers={'Content-type': 'application/x-www-form-urlencoded','Accept': 'text/plain'},ca_file=certifi.where(),verify=True,method='POST')

    def on_start(self):
        self.theme_cls.theme_style = "Dark" if self.settings["dark_theme"] == True else "Light"
        Window.bind(on_keyboard=self.key_handler)

        self.update_config()
        self.root.ids.version_label.text = f"Math Camera v {__version__}"

    #Обновление
    def download_content(self,download_url):
        filename = download_url.replace("?","/").split("/")[4]

        def update_progress(request, current_size, total_size):
            update_progress = round((current_size / total_size)*100)
            self.root.ids.update_progress.value = update_progress
            self.root.ids.update_percent.text='{}%'.format(update_progress)

        def unzip_content(req, result): 
            if platform == 'android':
                send_to_downloads(filename)

            popup = MDDialog(title='Загрузка завершена',text=f'Для обновления приложения следуйте инструкциям',buttons=[MDFlatButton(text="Открыть",theme_text_color="Custom",text_color=self.main_colors[0],on_release=lambda *args:webbrowser.open(self.config_["help_url"]+"update"))],auto_dismiss=False)
            popup.open()

        req = UrlRequest(download_url, on_progress=update_progress,chunk_size=1024, on_success=unzip_content,file_path=filename)

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
        self.chooser.choose_content('image/*', multiple = False)

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
        history = json.load(open('data/history.json'))[::-1]
        history_sw = self.root.ids.history_sw
        history_sw.clear_widgets()

        for elem in history:
            for equ_type,equ_text in elem.items():
                history_sw.add_widget(TwoLineListItem(text=self.menu_items[equ_type],secondary_text=equ_text,on_release=lambda s:self.send_equation(equ_text,equ_type)))

    def clear_history(self):
        with open("data/history.json","w") as file:
            json.dump([],file)
        self.load_history()

    def clear_cache(self):
        paths = ['mpl_tmp','xcamera_tmp']
        for path_name in paths:
            if os.path.exists(path_name):
                shutil.rmtree(path_name, ignore_errors=True)
        
        toast("Кеш очищен")

    def setup(self):
        ids = self.root.ids
        settings = self.settings
        for elem_id in settings.keys():
            ids[elem_id].active = settings[elem_id]

        ids["auto_flashlight"].disabled = not(ids["enable_flashlight"].active)

    def handle_switch(self,type,state):
        if type == "enable_flashlight":
            if state == False:
                self.root.ids["auto_flashlight"].active = False
            self.root.ids["auto_flashlight"].disabled = not(state)

        if type == "dark_theme":
            self.theme_cls.theme_style = "Dark" if state == True else "Light"

        self.settings[type] = state

        with open("data/settings.json","w") as file:
            file.write(json.dumps(self.settings))

    def key_handler(self, window, keycode,*args):
        manager = self.root.ids["sm"]
        if keycode in [27, 1001]:
            if manager.current != 'sc_home':
                self.set_screen(self.last_screen)
            return True
        return False

    def handle_camera(self):
        xcamera = self.root.ids['xcamera']
        enable_flashlight = self.settings["enable_flashlight"]
        auto_flashlight = self.settings["auto_flashlight"]

        state = "on" if enable_flashlight == True else "off"
        if auto_flashlight == True:state = "auto"

        xcamera.set_flashlight(state)
        self.root.ids.flashlight_btn.icon = self.flashlight_modes[state]

    def switch_flashlight_mode(self):
        max_len = len(self.flashlight_modes.keys())-1

        if list(self.flashlight_modes.keys()).index(self.root.ids.xcamera.flashlight_mode)+1 <= max_len:
            val = list(self.flashlight_modes.keys()).index(self.root.ids.xcamera.flashlight_mode)+1
        else:
            val = 0
            
        res = list(self.flashlight_modes.keys())[val]
        self.root.ids['xcamera'].set_flashlight(res)

        self.root.ids.flashlight_btn.icon = self.flashlight_modes[res]
        
        if res == "auto":
            self.settings["auto_flashlight"] = True
            self.settings["enable_flashlight"] = True

        elif res== "on":
            self.settings["enable_flashlight"] = True
            self.settings["auto_flashlight"] = False

        elif res == "off":
            self.settings["enable_flashlight"] = False
            self.settings["auto_flashlight"] = False

        with open("data/settings.json","w") as file:
            file.write(json.dumps(self.settings))

    def make_photo(self):
        try:
            self.root.ids['xcamera'].shoot()
        except:
            self.restart_camera()

    def restart_camera(self):
        if self.check_camera_perm() == True:
            try:
                xcamera = self.root.ids['xcamera']
                xcamera.play = False
                xcamera._camera._release_camera()
                xcamera._camera.init_camera()
                xcamera.play = True
            except Exception as e:
                err = e
                err = f"\n\n{e}" if self.settings["debug_mode"] == True else ""
                popup = MDDialog(title='Ошибка',text=f'Не удалось подключиться к камере. Перезагрузите приложение {err}',buttons=[MDFlatButton(text="Перезагрузить",theme_text_color="Custom",text_color=self.main_colors[0],on_release=lambda *args:self.stop())])
                popup.open()
        else:
            self.show_cam_alert_dialog()
            
    def check_camera_perm(self):
        return check_camera_permission()

    def request_camera_perm(self,*args):
        try:
            check_request_camera_permission()
            self.perm_dialog.dismiss()
        except:pass

    def open_browser(self,url):
        webbrowser.open(url)

    def show_cam_alert_dialog(self):
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
                    on_release=self.request_camera_perm,
                ),
            ],
        )
        self.perm_dialog.open()

    def set_screen(self,screen_name,*screen_title):
        if self.root.current == "main_sc":
            self.last_screen = self.root.ids['sm'].current
            
            self.root.ids['sm'].current = screen_name
            self.root.ids['tb'].title = self.screen_names[screen_name] if not screen_title else screen_title[0]
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

    def send_equation(self,*args):
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

                        else:
                            self.root.ids['plot_card'].visible = False
                    else:
                        self.root.ids['plot_card'].visible = False

                    self.root.ids["equation_label"].text = equation
                    self.root.ids["solution_label"].text = result["message"]

                    self.set_screen("sc_solve")

                    self.root.ids["equ_type_label"].text = self.menu_items[solver_type]

                    with open("data/history.json","r+") as file:
                        json_data = json.load(file)
                        json_data.append({solver_type:equation})
                        file.seek(0)
                        json.dump(json_data,file)
        
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
                        self.root.ids['textarea'].text = result
                
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

    @mainthread
    def picture_taken(self,obj,filename):
        image_data = obj.texture.pixels
        size = obj.texture.size
        pil_image = Image.frombytes(mode='RGBA', size=size,data=image_data)
        pil_image = pil_image.rotate(180)
        pil_image = pil_image.transpose(method=Image.FLIP_TOP_BOTTOM)
        buffered = BytesIO()
        pil_image.save(buffered,format='png')
        img = base64.b64encode(buffered.getvalue())
        self.send_b64(img)

if __name__ == "__main__":
    MathCamera().run()