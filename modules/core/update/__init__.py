import webbrowser
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog

def check_update(current_version,data):
    if current_version != data["latest_version"]:
        buttons = [MDFlatButton(text="Обновить",theme_text_color="Custom",text_color="#02714C",on_release=lambda *args:launch_update())]
        old = 'old' in data.keys()
        if old != True:
            buttons.append(MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color="#02714C",on_release=lambda *args:popup.dismiss()))

        popup = MDDialog(title='Доступно новое обновление',text=f'Вы хотите обновить приложение?',auto_dismiss=not old,buttons=buttons)
        popup.open()  

        def launch_update():
            webbrowser.open(data["download_url"])  