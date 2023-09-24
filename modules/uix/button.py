from kivy.clock import Clock
from kivy.lang import Builder
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import StringProperty, ListProperty,DictProperty

from kivymd.uix.button import MDIconButton
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

class CustomFlatIconButton(MDFlatButton):
    icon = StringProperty('android')
    bg_color = ListProperty((1, 1, 1, 0))


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


class LongPressIconButton(LongPressButton, MDIconButton):
    pass

class MultiModeFlatButton(LongPressButton, MDFlatButton):
    modes = ListProperty(['', ''])
    values = ListProperty(['',''])
    mode = 0

    def on_long_press(self):
        self.mode = (self.mode + 1) % len(self.modes)

        self.text = self.modes[self.mode]
        self.value = self.values[self.mode]

        super(MultiModeFlatButton, self).on_long_press()