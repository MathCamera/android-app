from kivy.clock import Clock
from kivy.lang import Builder
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import StringProperty, ListProperty,DictProperty,ObjectProperty
from kivymd.uix.menu import MDDropdownMenu
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
    long_press_time = .15
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
    modes = ListProperty(["",""])
    values = ListProperty(["",""])
    app = ObjectProperty()

    def on_long_press(self):
        elements = dict(zip(self.modes, self.values))
        menu_items = [
            {
                "text": elem,
                "on_release": lambda x=elements[elem]: handle_release(x),
                "font_name":"media/fonts/ArialMT.ttf",
            } for elem in elements
        ]

        def handle_release(x):
            menu.dismiss()

        menu = MDDropdownMenu(items=menu_items,caller=self)
        menu.open()

        super(MultiModeFlatButton, self).on_long_press()

#функции для работы с полем ввода
def edit_textfield(main,mode,text=""):
    textfield = main.root.ids.textarea
    textfield.focus=True
    if mode == "edit":
        main.root.ids.textarea.last_edit = textfield.text
        textfield.insert_text(text, from_undo=False)
        if len(text) > 1 and text[-1:] in [")"]:
            move_cursor(main,'left')

    if mode == "delete":
        main.root.ids.textarea.last_edit = textfield.text
        textfield.do_backspace(from_undo=False, mode='bkspc')

    if mode == "clear":
        main.root.ids.textarea.last_edit = textfield.text
        textfield.text = ""

    if mode == "undo":
        textfield.text = main.root.ids.textarea.last_edit

def move_cursor(main,direction):
    main.root.ids.textarea.do_cursor_movement(f"cursor_{direction}", control=False, alt=False)

def set_kb(main,kb_name):
    kb_manager = main.root.ids.kb.ids.kb_manager
    if kb_name == "next":
        if kb_manager.kb_list.index(kb_manager.current)+1 < len(kb_manager.kb_list):
            next_screen = kb_manager.kb_list[kb_manager.kb_list.index(kb_manager.current)+1]

        elif kb_manager.kb_list.index(kb_manager.current)+1 == len(kb_manager.kb_list):
            next_screen = kb_manager.kb_list[0]

        kb_manager.current = next_screen

    else:kb_manager.current = kb_name