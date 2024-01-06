import webbrowser
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog

def check_update(current_version,data,app):
    def launch_update():
        webbrowser.open(data["download_url"])
        
    if 'old' in data.keys():
        app.root.ids.update_app_btn.on_release=lambda: launch_update()
        app.set_screen("update_sc",root_=True)
        return False
    else:
        if int("".join(str(current_version).split("."))) < int("".join(str(data["latest_version"]).split("."))):
            popup = MDDialog(title='Доступно новое обновление',text=f'Вы хотите обновить приложение?',buttons=[MDFlatButton(text="Обновить",theme_text_color="Custom",text_color="#02714C",on_release=lambda *args:launch_update()),MDFlatButton(text="Закрыть",theme_text_color="Custom",text_color="#02714C",on_release=lambda *args:popup.dismiss())])
            popup.open()  
        return True