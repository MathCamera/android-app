from kivy.lang import Builder
from kivymd.app import MDApp

from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton

from kivymd.utils import asynckivy

from kivy.clock import mainthread
from kivy.network.urlrequest import UrlRequest
from kivy.core.window import Window

import base64,os,certifi,urllib.parse,json,webbrowser
from PIL import Image
from io import BytesIO

from kivy_garden.xcamera import XCamera
from kivy_garden.xcamera.xcamera import check_camera_permission,check_request_camera_permission,is_android
from kivy_garden.xcamera.platform_api import LANDSCAPE,PORTRAIT, set_orientation,check_flashlight_permission

XCamera._previous_orientation = set_orientation(PORTRAIT)
XCamera.directory = 'img'

OCR_API_URL = "https://mathcamera-api.vercel.app/api/ocr/tesseract"
MATH_API_URL = ""

class MathCamera(MDApp):
    main_col = "#02714C"
    perm_dialog = None
    prev_screen_data = {"sc_name":"sc_text","sc_title":"Главная"}
    def build(self):
        if not os.path.exists('img'):
            os.makedirs('img')

        self.settings = json.load(open('settings.json'))

        dark_theme = self.settings["dark_theme"]
        self.theme_cls.theme_style = "Dark" if dark_theme == True else "Light"
        self.theme_cls.primary_palette = "Green"

        Window.bind(on_keyboard=self.key_handler)

        return Builder.load_file('md.kv')

    def setup(self):
        ids = self.root.ids
        settings = self.settings
        for elem_id in settings.keys():
            ids[elem_id].active = settings[elem_id]

        #Убираем переключение темы
        #Пока не добаыим тёмную тему
        ids["dark_theme"].disabled = True
        ids["cam_high_quality"].disabled = True

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
        #auto/on/off
        high_quality = self.settings["cam_high_quality"]
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
        except Exception as e:
            err = e
            err = f"\n\n{e}" if self.settings["debug_mode"] == True else ""
            popup = MDDialog(title='Ошибка',text=f'Не удалось подключиться к камере. Перезагрузите приложение {err}',buttons=[MDFlatButton(text="Перезагрузить",theme_text_color="Custom",text_color=self.main_col,on_release=lambda *args:self.stop())])
            popup.open()
            
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

    def get_logs(self):
        logs_path = '.kivy/logs'
        r = os.listdir(logs_path)
        last_log = len(r)-2

        f = open(f"{logs_path}/{r[last_log]}", 'r')
        file_contents = f.read()
        f.close()
        return file_contents

    def get_response(self,b64):
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
            #Убираем лишние пробелы и переносы строк
            result = " ".join(str(result).split())

            if result == "":
                result_text = "Не удалось распознать текст на фото"
                alert_title = "Ошибка"
                
                popup = MDDialog(title=alert_title,text='{}'.format(result_text),buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color=self.main_col,on_release=lambda *args:popup.dismiss())])
                popup.open()
                
            else:
                self.set_screen("sc_text","Ввести уравнение")
                self.root.ids['textarea'].text = result

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
        #Получаем бинарные данные картинки
        image_data = obj.texture.pixels
        size = obj.texture.size
        #Загружаем фото в переменную pil_image
        pil_image = Image.frombytes(mode='RGBA', size=size,data=image_data)
        #Вертикально отзеркаливаем картинку
        pil_image = pil_image.rotate(180)
        pil_image = pil_image.transpose(method=Image.FLIP_TOP_BOTTOM)
        buffered = BytesIO()
        pil_image.save(buffered,format='png')
        #Переводим картинку в base64 для отправки на сервер
        img = base64.b64encode(buffered.getvalue())
        #Удаляем картинку из директории приложения
        os.remove(filename)
        self.get_response(img)

if __name__ == "__main__":
    MathCamera().run()