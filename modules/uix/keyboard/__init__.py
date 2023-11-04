from kivy.clock import Clock
from kivy.lang import Builder
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import StringProperty, ListProperty,DictProperty

from kivymd.uix.button import MDFlatButton

Builder.load_string('''
#:import MDIcon kivymd.uix.label.MDIcon
<CustomFlatIconButton>:
    mdicon:mdicon
    canvas.before:
        Color:
            rgba: self.bg_color
        Rectangle:
            pos: self.pos
            size: self.size
    size_hint: None, 1
    MDIcon:
        id: mdicon
        icon: root.icon
        size_hint: 1, 1
        halign: 'center'
        theme_text_color: 'Primary'
                    
''')

class LongPressButton(ButtonBehavior):
    __events__ = ('on_long_press', 'on_short_press')
    long_press_time = .2
    is_long_pressed = False

    def on_state(self, instance, value):
        if value == 'down':
            self._clockev = Clock.schedule_once(self._do_long_press,
                                                self.long_press_time)
        else:
            self._clockev.cancel()

    def _do_long_press(self, dt):
        self.dispatch('on_long_press')

    def on_long_press(self, *largs):
        self.is_long_pressed = True

    def _do_short_press(self):
        self.dispatch('on_short_press')

    def on_short_press(self, *largs):
        pass

    def on_release(self):
        if self.is_long_pressed:
            self.is_long_pressed = False
        else:
            self._do_short_press()

class CustomFlatIconButton(LongPressButton,MDFlatButton):
    icon = StringProperty('android')
    bg_color = ListProperty((1, 1, 1, 0))

class MultiModeFlatButton(LongPressButton, MDFlatButton):
    modes = ListProperty(['', ''])
    values = ListProperty(['',''])
    mode = 0

    def on_long_press(self):
        self.mode = (self.mode + 1) % len(self.modes)

        self.text = self.modes[self.mode]
        self.value = self.values[self.mode]

        super(MultiModeFlatButton, self).on_long_press()

#функции для работы с полем ввода
def edit_textfield(main,mode,text=None,move_cursor=0):
    if mode == "edit":
        textfield = main.root.ids.textarea
        main.root.ids.textarea.last_edit = main.root.ids.textarea.text
        cursor_index = int(textfield.cursor[0])
        textfield.text = textfield.text[:textfield.cursor[0]] + text + textfield.text[textfield.cursor[0]:]
        textfield.cursor = (cursor_index+len(text)-move_cursor,0)

    if mode == "delete":
        main.root.ids.textarea.last_edit = main.root.ids.textarea.text
        textfield = main.root.ids.textarea
        cursor_index = int(textfield.cursor[0])
        if cursor_index > 0:
            textfield.text = textfield.text[:(cursor_index-1)] + textfield.text[cursor_index:]
        textfield.cursor = (cursor_index-1,0)

    if mode == "clear":
        main.root.ids.textarea.text = ""

    if mode == "undo":
        main.root.ids.textarea.text = main.root.ids.textarea.last_edit

def move_cursor(main,direction):
    cursor = main.root.ids.textarea.cursor
    max_index = len(main.root.ids.textarea.text)+1

    if direction == "right":
        cursor_pos = cursor[0]+1 if cursor[0]+1 < max_index else 0

    if direction == "left":
        cursor_pos = cursor[0]-1 if cursor[0]-1 >= 0 else max_index

    main.root.ids.textarea.cursor = (cursor_pos,0)

def set_kb(main,kb_name):
    kb_manager = main.root.ids.kb.ids.kb_manager
    if kb_name == "next":
        if kb_manager.kb_list.index(kb_manager.current)+1 < len(kb_manager.kb_list):
            next_screen = kb_manager.kb_list[kb_manager.kb_list.index(kb_manager.current)+1]

        elif kb_manager.kb_list.index(kb_manager.current)+1 == len(kb_manager.kb_list):
            next_screen = kb_manager.kb_list[0]

        kb_manager.current = next_screen

    else:kb_manager.current = kb_name