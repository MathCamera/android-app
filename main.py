__version__ = "1.3.0"

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
from kivy.uix.image import AsyncImage

from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.list import TwoLineListItem,MDList
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard

from modules.platform_api import request_camera_permission,set_orientation
from modules.core.update import check_update
from modules.xcamera import *
from modules.uix.loadingdialog import LoadingDialog

import base64,os,certifi,urllib.parse,json,webbrowser,shutil
from PIL import Image
from io import BytesIO
from random import randint

if platform == "android":
    from androidstorage4kivy import Chooser,SharedStorage
    from kvdroid.tools import change_statusbar_color,toast,navbar_color
    from kvdroid.tools.darkmode import dark_mode
    from kvdroid.tools import share_text
    change_statusbar_color("#02714C", "white")
else:
    def toast(text):
        print(text)

    def navbar_color(color):
        pass

    def dark_mode():
        return False

    Window.size = (400,700)

class app_main(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.version_ = __version__
        self.data_dir = os.path.join("..","user_data")
        self.theme_cls.colors = json.load(open('data/themes.json'))
        self.theme_cls.material_style = "M3"
        self.main_colors = ["#02714C","#039866"]
        self.last_screen,self.last_equation,self.config_ = None,None,{'config_url':"https://mathcamera-api.vercel.app/config"}
        self.deeplink=""

    def build(self):        
        return Builder.load_file('style.kv')
    
    def on_start(self):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            self.set_screen("onboarding_sc",root_=True)
        else:
            self.update_config()
    
        self.settings = JsonStore(os.path.join(self.data_dir,'settings.json'))
        self.history = JsonStore(os.path.join(self.data_dir,'history.json'))

        if list(json.load(open('data/settings.json')).keys()) != self.settings.keys():
            self.set_settings(reset=True)

        request_camera_permission()
        set_orientation()
        
        Window.bind(on_keyboard=self.key_handler)
        self.root.ids.preview.connect_camera(enable_video = False,filepath_callback=self.handle_image,enable_analyze_pixels=True,default_zoom=0)
        
        self.theme_cls.theme_style = "Dark" if dark_mode() == True else "Light"
        navbar_color("#121212" if dark_mode() == True else "#FFFFFF")

        if platform == "android":
            self.verify_message_at_startup()
            self.chooser = Chooser(self.chooser_callback)

        self.loader_image_path = "media/loader.png"
        Loader.loading_image = self.loader_image_path
        Logger.info(f"App version: {__version__}")

    def on_stop(self):
        self.root.ids.preview.disconnect_camera()

    def show_menu(self):
        self.root.ids.nav_drawer.set_state("open")
        self.root.ids.textarea.focus=False

    def share_text(self,text):
        if platform == "android":
            share_text(text, title="Поделиться", chooser=True, app_package=None,call_playstore=False, error_msg="Не удалось отправить сообщение")

        print(text)
    def show_network_error(self,retry_func):
        self.root.ids.connection_error_retry.on_release=lambda: retry_func
        self.set_screen('loading_sc_error',root_=True)

    def update_config(self):
        def success(req,result):
            self.set_screen("main_sc",root_=True)

            for elem in result.keys():
                self.config_[elem] = result[elem]

            check_update(__version__,result)
            Logger.info(f"Api server response: {result}")
            
            if self.deeplink != "":
                self.process_deep_link(self.deeplink)
        
        def error(req, result):
            self.show_network_error(self.update_config())

        req = UrlRequest(self.config_['config_url'],on_success=success,on_failure=error,on_error=error,req_body=urllib.parse.urlencode({'version':self.version_}),req_headers={'Content-type': 'application/x-www-form-urlencoded','Accept': 'text/plain'},ca_file=certifi.where(),verify=True,method='POST')

    def verify_message_at_startup(self):
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity
        intent = activity.getIntent()
        self.android_message(intent)

    @mainthread
    def android_message(self, intent):
        intent_data = intent.getData()
        try:
            uri = intent_data.toString()
            self.deeplink = uri
        except AttributeError:
            pass

    def process_deep_link(self, uri):
        Logger.info("Raw deeplink: "+str(uri))

        url = urllib.parse.urlparse(urllib.parse.unquote(uri))
        if url.scheme == "mathcamera":
            if url.netloc == "s":
                uri_data = url.path[1:]
            
            elif url.netloc == "w":
                uri_data = url.path[1:][:-3]
            
            else:uri_data = ""
        
        elif url.scheme in ['http','https'] and url.netloc in ['mathcamera.vercel.app','mathcamera.ru']:
            uri_data = url.path.replace("/s/","")
        
        else:uri_data = ""

        Logger.info("Deeplink: "+str(uri_data))

        if uri_data != "":
            self.send_equation(uri_data)

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
            if self.history.count() != 0:
                history_sw = MDList()
                self.root.ids.history_clear_btn.disabled = False
                self.root.ids.history_layout.add_widget(history_sw)

                for ind,elem in enumerate(self.history):
                    list_item = TwoLineListItem(text=self.history[elem]['equ_type'],secondary_text=self.history[elem]['as_latex'],on_release=lambda s:self.send_equation(s.equ_main,from_history=True))
                    list_item.equ_main=self.history[elem]['equation']
                    history_sw.add_widget(list_item,ind)

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
            if manager.current == 'sc_photo' or manager.current==self.last_screen:
                self.stop()
            else:
                self.set_screen(self.last_screen)
            return True
        return False
    
    def photo(self):
        self.root.ids.preview.capture_photo(location="private",subdir="camera_tmp")

    def switch_flashlight_mode(self):
        camera = self.root.ids.preview
        if camera.camera_connected == True:
            flashlight_modes = {"on":"flash","off":"flash-off"}
            camera.flashlight_mode = "on" if camera.flashlight_mode == "off" else "off"
            icon = self.root.ids.preview.flash(camera.flashlight_mode)
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

    def get_logs(self):
        logs_path = shutil.make_archive('logs', 'zip', root_dir='.kivy/logs')
        ss = SharedStorage()
        ss.copy_to_shared(logs_path,filepath='/logs')
        toast(f"Логи выгружены: Documents/MathCamera/logs")

    def set_screen(self,screen_name,*screen_title,root_=False):
        self.root.ids['nav_drawer'].set_state("closed")
        self.root.ids.textarea.focus=False
        if not root_:
            if self.root.current == "main_sc":
                self.last_screen = self.root.ids['sm'].current
                self.root.ids['sm'].current = screen_name
                if screen_title:
                    self.root.ids['tb'].title = screen_title[0]
        else:
            self.root.current = screen_name

    def show_adv(self):
        adv_index = randint(1,len(self.config_['adv_urls']))
        self.root.ids.adv_card.on_release = lambda:self.open_browser(self.config_["adv_urls"][adv_index-1])
        self.root.ids.adv_image.source = self.config_['adv_url'].format(adv_index)
    
    def send_equation(self,*args,from_history=False):            
        equation = args[0] if args else self.root.ids.textarea.text

        if equation != "" and equation != self.last_equation:
            self.root.ids.textarea.focus = False

            loading_popup = LoadingDialog(title="Загрузка",auto_dismiss=False)
            if self.root.current != "loading_sc_error" :
                loading_popup.open()

            params = urllib.parse.urlencode({'src':equation})

            def success(req, result):
                self.root.current = "main_sc"
                status_code = result['status_code']

                if status_code == 0:
                    gamma_result = result['message']
                    self.root.ids.gl.clear_widgets()
                    equation_as_latex = str(gamma_result[0]['output']).replace(" ","")
                    equation_main = str(gamma_result[0]['input'])
                    has_plot = False

                    #Загрузка карточек и графика
                    for card in gamma_result:
                        #valid_card = ("title" in card.keys() and card['title'] != "") and ("output" in card.keys() and card['output'] != "")
                        contains_plot = 'card' in list(card.keys()) and card['card'] == "plot"
                        if contains_plot:has_plot=True

                        kv_card = MDCard(orientation="vertical",pos_hint={"top":1},md_bg_color="#039866",padding=[30,15,30,15],size_hint_y=None,spacing=10)
                        title_label = MDLabel(text=f"{card['title']}:",adaptive_height=True,theme_text_color="Custom",text_color="white",font_style="H6",bold=True)
                        kv_card.add_widget(title_label)

                        if contains_plot:
                            plot_url = self.config_["plotting_url"].format(str(card['input']).replace(" ",""))
                            
                            def on_load(image_widget):
                                if image_widget.texture.size != (1,1):
                                    plot_card = image_widget.parent
                                    self.root.ids.gl.add_widget(plot_card,len(self.root.ids.gl.ids)-1)
                                    image_widget.remove_from_cache()

                                loading_popup.dismiss()
                                self.set_screen("sc_solve")

                            image_widget = AsyncImage(source=plot_url,on_load=on_load,fit_mode="cover")
                            kv_card.height = dp(kv_card.height*1.5)+dp(image_widget.height*1.5)
                            kv_card.add_widget(image_widget)

                        else:
                            kv_card.adaptive_height = True
                            result_text = card['output'] if 'output' in card.keys() else ""
                            output_label = MDLabel(text=result_text,adaptive_height=True,theme_text_color="Custom",text_color="white",font_style="Subtitle1")
                            output_label.font_name = "media/fonts/NotoSansMath-Regular.ttf"
                            kv_card.add_widget(output_label)

                            self.root.ids.gl.add_widget(kv_card)

                    self.root.ids.gl.problem_main = equation_main
                    self.root.ids.gl.problem_input = equation
                    self.root.ids.gl.share_url = self.config_['share_url'].format(urllib.parse.quote_plus(equation.replace(" ","")))

                    if from_history == False:
                        self.history[self.history.count()+1] = {"equ_type":gamma_result[0]['title'],"equation":equation,"as_latex":equation_as_latex}

                    if not has_plot:
                        loading_popup.dismiss()
                        self.set_screen("sc_solve")

                    self.last_equation = equation
                else:
                    loading_popup.dismiss()
                    err = f"\n\n{result}" if self.settings["enable_debug_mode"]['mode'] == True else ""
                    popup = MDDialog(text=f'Не удалось решить задачу, проверьте правильность введённых данных{err}',buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color="#02714C",on_release=lambda *args:popup.dismiss())])
                    popup.open()   

            def on_failure(req,res):
                loading_popup.dismiss()
                err = f"\n\n{res}" if self.settings["enable_debug_mode"]['mode'] == True else ""
                popup = MDDialog(text=f'Не удалось решить задачу, проверьте правильность введённых данных{err}',buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color="#02714C",on_release=lambda *args:popup.dismiss())])
                popup.open()  

            def error(req, result):
                print(req)
                loading_popup.dismiss()
                Logger.error("Send equation error: "+str(result))
                self.show_network_error(self.send_equation(equation))

            if self.last_equation == equation:
                self.set_screen("sc_solve")
            else:
                req = UrlRequest(self.config_["math_solve_url"],on_success=success,on_failure=on_failure,on_error=error,req_body=params,req_headers={'Content-type': 'application/x-www-form-urlencoded','Accept': 'text/plain'},ca_file=certifi.where(),verify=True,method='POST')

    def send_b64(self,b64):
        loading_popup = LoadingDialog(title="Загрузка",auto_dismiss=False)
        if self.root.current != "loading_sc_error":
            loading_popup.open()

        params = urllib.parse.urlencode({'src':b64})

        def success(req, result):
            self.root.current = "main_sc"
            if result['status_code'] == 0:
                loading_popup.dismiss()
                if result['message'] == "":
                    popup = MDDialog(text="Не удалось распознать задачу",buttons=[MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color="#02714C",on_release=lambda *args:popup.dismiss())])
                    popup.open()
                    
                else:
                    self.set_screen("sc_text")
                    self.root.ids.textarea.text = result["message"]
                
            else:error(req,result)

        def error(req, result):
            loading_popup.dismiss()
            Logger.error("Send b64 error: "+str(result))
            self.show_network_error(self.send_b64(b64))

        ocr_url = self.config_["debug_server_url"] if self.settings["enable_test_server"]['mode'] == True else self.config_["ocr_url"]
        req = UrlRequest(ocr_url,on_success=success,on_failure=error,on_error=error,req_body=params,req_headers={'Content-type': 'application/x-www-form-urlencoded','Accept': 'text/plain'},ca_file=certifi.where(),verify=True,method='POST')

if __name__ == '__main__':
    app_ = app_main()
    if platform == 'android':
        import android.activity
        android.activity.bind(on_new_intent=app_.android_message)
    app_.run()