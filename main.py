from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.clock import mainthread
from kivy.utils import platform
from kivymd.toast import toast
from kivy.core.window import Window

from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.menu import MDDropdownMenu

from modules.xcamera import XCamera
from modules.xcamera.xcamera import check_camera_permission,check_request_camera_permission,is_android
from modules.xcamera.platform_api import PORTRAIT, set_orientation,check_flashlight_permission
from modules.urlrequest.urlrequest import UrlRequest
from modules.plotting import render_plot

import base64,os,certifi,urllib.parse,json,webbrowser,shutil,math
from packaging import version
from PIL import Image
from io import BytesIO

XCamera._previous_orientation = set_orientation(PORTRAIT)

if platform != "android":
    Window.size = (360,600)

class MathCamera(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prev_screen_data = {"sc_name":"sc_text","sc_title":"Главная"}
        self.menu_items = {"digit":"Решить пример","equation":"Решить уравнение","system":"Решить систему уравнений","simplify":"Упростить выражение"}
        self.solver_type = None

    def build(self):
        self.config = json.load(open('data/config.json'))

        self.theme_cls.primary_palette = "Green"
        self.theme_cls.material_style = "M2"

        return Builder.load_file('data/md.kv')
    
    def update_config(self):
        headers = {'Content-type': 'application/x-www-form-urlencoded','Accept': 'text/plain'}

        def success(req,result):
            result = json.loads(result)
            self.config["math_solve_url"] = result["math_solve_url"]
            self.config["ocr_url"] = result["ocr_url"]
            self.config['download_url'] = result["download_url"]
        
            if version.parse(self.config["current_version"]) < version.parse(result["latest_version"]):
                popup = MDDialog(title='Доступно новое обновление',text=f'Вы хотите обновить приложение?',buttons=[MDFlatButton(text="Обновить",theme_text_color="Custom",text_color=self.config["main_color"],on_release=lambda *args:webbrowser.open(self.config['download_url'])),MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color=self.config["main_color"],on_release=lambda *args:popup.dismiss())])
                popup.open()  
            
            with open("data/config.json","w") as file:
                file.write(json.dumps(self.config))            

        req = UrlRequest(self.config['config_url'],on_success=success,req_headers=headers,ca_file=certifi.where(),verify=True,method='POST')

    def on_start(self):
        self.settings = json.load(open('data/settings.json'))

        self.theme_cls.theme_style = "Dark" if self.settings["dark_theme"] == True else "Light"
        Window.bind(on_keyboard=self.key_handler)

        self.update_config()

    def set_kb(self,kb_name):
        kb_manager = self.root.ids.kb_manager
        screens_list = ["main_kb","letters_kb"]
        if kb_name == "next":
            if screens_list.index(kb_manager.current)+1 < len(screens_list):
                next_screen = screens_list[screens_list.index(kb_manager.current)+1]

            elif screens_list.index(kb_manager.current)+1 == len(screens_list):
                next_screen = screens_list[0]

            kb_manager.current = next_screen

        else:
            kb_manager.current = kb_name

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
                self.set_screen(self.prev_screen_data["sc_name"],self.prev_screen_data["sc_title"])
            return True
        return False

    def handle_camera(self):
        #self.restart_camera()
        #high_quality = self.settings["cam_high_quality"]
        xcamera = self.root.ids['xcamera']
        enable_flashlight = self.settings["enable_flashlight"]
        auto_flashlight = self.settings["auto_flashlight"]

        state = "on" if enable_flashlight == True else "off"
        if auto_flashlight == True:state = "auto"

        xcamera.set_flashlight(state)
        #xcamera.resolution = 640, 480 if high_quality == False else 1920, 1080

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
                popup = MDDialog(title='Ошибка',text=f'Не удалось подключиться к камере. Перезагрузите приложение {err}',buttons=[MDFlatButton(text="Перезагрузить",theme_text_color="Custom",text_color=self.config["main_color"],on_release=lambda *args:self.stop())])
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
                    text_color=self.config["main_color"],
                    on_release=lambda *args:self.perm_dialog.dismiss(),
                ),
                MDFlatButton(
                    text="Разрешить",
                    theme_text_color="Custom",
                    text_color=self.config["main_color"],
                    on_release=self.request_camera_perm,
                ),
            ],
        )
        self.perm_dialog.open()

    def set_screen(self,screen_name,title):
        self.prev_screen_data["sc_name"] = self.root.ids['sm'].current
        self.prev_screen_data["sc_title"] = self.root.ids['tb'].title
        
        self.root.ids['sm'].current = screen_name
        self.root.ids['tb'].title = title
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

    def on_text_screen(self):
        menu_items = [
            {
                "viewclass": "OneLineListItem",
                "text": i,
                "height": 56,
                "on_release": lambda x=i: set_item(x),
            } for i in self.menu_items.values()]

        self.menu = MDDropdownMenu(
            caller=self.root.ids.drop_item,
            items=menu_items,
            position="bottom",
            width_mult=4,
        )
        self.menu.bind()

        def set_item(text_item):
            self.root.ids.drop_item.set_item(text_item)
            self.menu.dismiss()
            self.solver_type = list(self.menu_items.keys())[list(self.menu_items.values()).index(text_item)]

    def send_equation(self,equation):
        if equation != "" and self.solver_type!= None:
            self.root.ids.textarea.ids.text_field.focus = False
            try:
                #Оффлайн решение
                #Преобразуем уравнение
                res = eval(str(equation).replace("√","math.sqrt").replace("π","math.pi").replace("sin","math.sin").replace("cos","math.cos").replace("tan","math.tan").replace("^","**").replace("G","9.80665"))
                self.root.ids["equation_label"].text = str(equation)
                #self.root.ids["equ_type_label"].text = "Решить пример:"
                self.root.ids["solution_label"].text = str(res)
                self.set_screen("sc_solve","Решение")
                self.root.ids['plot_card'].visible = False

            except:
                loading_popup = MDDialog(title='Загружаем данные',text='Загрузка...')
                loading_popup.open()

                params = urllib.parse.urlencode({'src':equation,"type":self.solver_type})
                headers = {'Content-type': 'application/x-www-form-urlencoded','Accept': 'text/plain'}

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

                        self.set_screen("sc_solve","Решение")
        
                    else:
                        err = f"\n\n{result}" if self.settings["debug_mode"] == True else ""
                        popup = MDDialog(title='Ошибка',text=f'Не удалось решить задачу, проверьте правильность введённых данных{err}',buttons=[MDFlatButton(text="Помощь",theme_text_color="Custom",text_color=self.config["main_color"],on_release=lambda *args:webbrowser.open(self.config["help_url"]+self.solver_type)),MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color=self.config["main_color"],on_release=lambda *args:popup.dismiss())])
                        popup.open()   

                self.root.ids["equ_type_label"].text = self.menu_items[self.solver_type]

                def error(req, result):
                    loading_popup.dismiss()
                    result = str(result).replace("\n","")
                    err = f"\n\n{result}" if self.settings["debug_mode"] == True else ""
                    popup = MDDialog(title='Ошибка',text=f'Не удаётся получить ответ от сервера,\nпроверьте подключение к интернету{err}',buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color=self.config["main_color"],on_release=lambda *args:popup.dismiss())])
                    popup.open()
                
                req = UrlRequest(self.config["math_solve_url"],on_success=success,on_failure=error,on_error=error,req_body=params,req_headers=headers,ca_file=certifi.where(),verify=True,method='POST')
            
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
        loading_popup = MDDialog(title='Загружаем данные',text='Загрузка...')
        loading_popup.open()

        params = urllib.parse.urlencode({'src':b64,'lang':'eng'})
        headers = {'Content-type': 'application/x-www-form-urlencoded','Accept': 'text/plain'}

        def success(req, result):
            global result_text
            #Скрываем уведомление с загрузкой
            loading_popup.dismiss()
            result = json.loads(result)
            status_code = result['status_code']
            result = result["message"]

            if status_code == 0:
                #Убираем лишние пробелы и переносы строк
                result = " ".join(str(result).split())

                if result == "":
                    popup = MDDialog(title="Ошибка",text="Не удалось распознать текст на фото",buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color=self.config["main_color"],on_release=lambda *args:popup.dismiss())])
                    popup.open()
                
                else:
                    self.set_screen("sc_text","Ввести уравнение")

                    #Обрезаем текст, если его длина больше 50 символов
                    if len(result) > 50: result = result[-50:]

                    self.root.ids['textarea'].text = result
            
            else:
                popup = MDDialog(title="Ошибка",text='{result}\nStatus code: {st_code}'.format(result=result,st_code=status_code),buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color=self.config["main_color"],on_release=lambda *args:popup.dismiss())])
                popup.open()

        def error(req, result):
            #Скрываем уведомление с загрузкой
            loading_popup.dismiss()
            result = str(result).replace("\n","")
            err = f"\n\n{result}" if self.settings["debug_mode"] == True else ""
            popup = MDDialog(title='Ошибка',text=f'Не удаётся получить ответ от сервера,\nпроверьте подключение к интернету{err}',buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color=self.config["main_color"],on_release=lambda *args:popup.dismiss())])
            popup.open()
        
        req = UrlRequest(self.config["ocr_url"],on_success=success,on_failure=error,on_error=error,req_body=params,req_headers=headers,ca_file=certifi.where(),verify=True,method='POST')

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