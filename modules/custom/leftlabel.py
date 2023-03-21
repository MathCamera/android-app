from kivy.uix.label import Label

class LeftLabel(Label):
    def on_size(self, *args):
        self.text_size = self.size