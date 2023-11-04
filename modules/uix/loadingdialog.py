from kivymd.uix.dialog import MDDialog
from kivymd.uix.progressbar import MDProgressBar
from kivy.uix.screenmanager import Screen

class LoadingDialog(MDDialog):
    def __init__(self,title,auto_dismiss=False):

        self.title = title
        self.auto_dismiss = auto_dismiss
        self.type = "custom"
        self.content_cls = Screen()
        self.progress_bar = MDProgressBar(type="indeterminate")
        self.content_cls.add_widget(self.progress_bar)
        self.progress_bar.start()

        super().__init__()