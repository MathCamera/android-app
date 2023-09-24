from kivy.uix.boxlayout import BoxLayout
from kivy.lang import Builder

class ReportDialog(BoxLayout):
    def get_data(self):
        #print(self.ids.field_1.height)
        return self.ids.field_1.text,self.ids.field_2.text
    
    def set_message(self,text):
        self.ids.field_2.text = text

Builder.load_string("""
<ReportDialog>
    orientation: "vertical"
    spacing: "12dp"
    size_hint_y: None
    height:"120dp"

    MDTextField:
        id:field_1
        required:True
        hint_text: "Как с вами связаться?"
        error:False
        #mode:"rectangle"
        max_text_length:50
        pos_hint:{"top":1}

    MDTextField:
        id:field_2
        required:True
        hint_text: "Опишите проблему"
        error:False
        max_height:"100dp"
        #mode:"rectangle"
        #multiline:True
        max_text_length:200
        pos_hint:{"top":1}
""")