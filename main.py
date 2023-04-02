from kivy.lang import Builder
from kivy.clock import mainthread
from kivy.core.window import Window
from kivy.utils import platform

from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.toast import toast

from modules.xcamera import XCamera
from modules.xcamera.xcamera import check_camera_permission,check_request_camera_permission,is_android
from modules.xcamera.platform_api import PORTRAIT, set_orientation,check_flashlight_permission
from modules.urlrequest.urlrequest import UrlRequest
from modules.plotting import render_plot

import base64,os,certifi,urllib.parse,json,webbrowser,shutil
from PIL import Image
from io import BytesIO

XCamera._previous_orientation = set_orientation(PORTRAIT)
#XCamera.directory = 'xcamera_tmp'

OCR_API_URL = "https://mathcamera-api.vercel.app/api/ocr/tesseract"
MATH_API_URL = "https://mathcamera-api.vercel.app/api/math/solve"

if platform != "android":
    Window.size = (360,600)

class MathCamera(MDApp):
    main_col = "#02714C"
    prev_screen_data = {"sc_name":"sc_text","sc_title":"Главная"}
    settings = json.load(open('settings.json'))

    def build(self):
        self.theme_cls.theme_style = "Dark" if self.settings["dark_theme"] == True else "Light"
        self.theme_cls.primary_palette = "Green"
        self.theme_cls.material_style = "M2"

        Window.bind(on_keyboard=self.key_handler)

        return Builder.load_file('md.kv')
    
    #Функция вызывается при окончании загрузки
    def on_start(self):
        pass

    def clear_cache(self):
        paths = ['mpl_tmp','xcamera_tmp']
        total_size = 0
        for path_name in paths:
            if os.path.exists(path_name):
                shutil.rmtree(path_name, ignore_errors=True)
        
        toast("Кеш очищен")

    def setup(self):
        ids = self.root.ids
        settings = self.settings
        for elem_id in settings.keys():
            ids[elem_id].active = settings[elem_id]

        #Убираем переключение темы, пока не добавим тёмную тему
        #ids["dark_theme"].disabled = True

        ids["auto_flashlight"].disabled = not(ids["enable_flashlight"].active)

    def handle_switch(self,type,state):
        if type == "enable_flashlight":
            if state == False:
                self.root.ids["auto_flashlight"].active = False
            self.root.ids["auto_flashlight"].disabled = not(state)

        if type == "dark_theme":
            self.theme_cls.theme_style = "Dark" if state == True else "Light"

        self.settings[type] = state

        with open("settings.json","w") as file:
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
                popup = MDDialog(title='Ошибка',text=f'Не удалось подключиться к камере. Перезагрузите приложение {err}',buttons=[MDFlatButton(text="Перезагрузить",theme_text_color="Custom",text_color=self.main_col,on_release=lambda *args:self.stop())])
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
                    text_color=self.main_col,
                    on_release=lambda *args:self.perm_dialog.dismiss(),
                ),
                MDFlatButton(
                    text="Разрешить",
                    theme_text_color="Custom",
                    text_color=self.main_col,
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

        #Костыль для деактивации поля ввода задачи (sc_text>text_field)
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

    def send_equation(self,equation):
        if self.root.ids.textarea.ids.text_field.text != "":
            self.root.ids.textarea.ids.text_field.focus = False
            loading_popup = MDDialog(title='Загружаем данные',text='Загрузка...')
            loading_popup.open()

            params = urllib.parse.urlencode({'src':equation})
            headers = {'Content-type': 'application/x-www-form-urlencoded','Accept': 'text/plain'}

            def success(req, result):
                loading_popup.dismiss()
                status_code = result['status_code']
                codes_list = {"equation":"Решить уравнение","digital":"Решить пример"}
                if status_code == 0:
                    res = result["message"]
                    equ_type = result['type']
                    self.set_screen("sc_solve","Решение")
                    
                    if "plot" in result.keys():
                        plot_filename = render_plot(result['plot'])
                        if plot_filename != None:
                            self.root.ids["plot_img"].source = plot_filename
                            self.root.ids['plot_card'].visible = True
                        
                    else:
                        self.root.ids['plot_card'].visible = False

                    self.root.ids["equation_label"].text = equation
                    self.root.ids["equ_type_label"].text = codes_list[equ_type]+":"
                    self.root.ids["solution_label"].text = res
    
                else:
                    err = f"\n\n{result}" if self.settings["debug_mode"] == True else ""
                    popup = MDDialog(title='Ошибка',text=f'Не удалось решить задачу, проверьте правильность введённых данных{err}',buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color=self.main_col,on_release=lambda *args:popup.dismiss())])
                    popup.open()     

            def error(req, result):
                loading_popup.dismiss()
                result = str(result).replace("\n","")
                err = f"\n\n{result}" if self.settings["debug_mode"] == True else ""
                popup = MDDialog(title='Ошибка',text=f'Не удаётся получить ответ от сервера,\nпроверьте подключение к интернету{err}',buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color=self.main_col,on_release=lambda *args:popup.dismiss())])
                popup.open()
            
            req = UrlRequest(MATH_API_URL,on_success=success,on_failure=error,on_error=error,req_body=params,req_headers=headers,ca_file=certifi.where(),verify=True,method='POST')
        
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
                    popup = MDDialog(title="Ошибка",text="Не удалось распознать текст на фото",buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color=self.main_col,on_release=lambda *args:popup.dismiss())])
                    popup.open()
                
                else:
                    self.set_screen("sc_text","Ввести уравнение")

                    #Обрезаем текст, если его длина больше 34 символов
                    if len(result) > 34: result = result[-34:]

                    self.root.ids['textarea'].text = result
            
            else:
                popup = MDDialog(title="Ошибка",text='{result}\nStatus code: {st_code}'.format(result=result,st_code=status_code),buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color=self.main_col,on_release=lambda *args:popup.dismiss())])
                popup.open()

        def error(req, result):
            #Скрываем уведомление с загрузкой
            loading_popup.dismiss()
            result = str(result).replace("\n","")
            err = f"\n\n{result}" if self.settings["debug_mode"] == True else ""
            popup = MDDialog(title='Ошибка',text=f'Не удаётся получить ответ от сервера,\nпроверьте подключение к интернету{err}',buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color=self.main_col,on_release=lambda *args:popup.dismiss())])
            popup.open()
        
        req = UrlRequest(OCR_API_URL,on_success=success,on_failure=error,on_error=error,req_body=params,req_headers=headers,ca_file=certifi.where(),verify=True,method='POST')

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