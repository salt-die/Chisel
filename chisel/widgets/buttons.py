from pathlib import Path

from kivy.uix.button import Button as KivyButton
from kivy.uix.button import ButtonBehavior
from kivy.uix.image import Image
from kivy.core.window import Window
from kivy.uix.behaviors import ToggleButtonBehavior

from .mixins import SignBorder

IMAGE_PATH = Path("assets", "img")
BUTTON_NORMAL = str(IMAGE_PATH / "button" / "normal.png")
BUTTON_HOVER = str(IMAGE_PATH / "button" / "hover.png")
BUTTON_PRESSED = str(IMAGE_PATH / "button" / "pressed.png")
BURGER_NORMAL = str(IMAGE_PATH / "burger" / "normal.png")
BURGER_HOVER = str(IMAGE_PATH / "burger" / "hover.png")
BURGER_PRESSED = str(IMAGE_PATH / "burger" / "pressed.png")


class Button(SignBorder, KivyButton):
    def __init__(self, text, font_name, **kwargs):
        super().__init__(text=text,
                         font_name=font_name,
                         outline_color=(0, 0, 0),
                         outline_width=2,
                         halign="center",
                         valign="middle",
                         **kwargs)
        self.setup_border()

        self.bind(size=self._on_size)
        Window.bind(mouse_pos=self._on_mouse_pos)

        self.background_normal = BUTTON_NORMAL
        self.background_down = BUTTON_PRESSED

    def _on_mouse_pos(self, *args):
        if self.collide_point(*self.to_widget(*Window.mouse_pos)):
            self.background_normal = BUTTON_HOVER
        else:
            self.background_normal = BUTTON_NORMAL

    def _on_size(self, *args):
        self.text_size = self.size


class BurgerButton(ButtonBehavior, Image):
    def __init__(self):
        super().__init__(source=BURGER_NORMAL, size_hint=(None, None))

        Window.bind(mouse_pos=self._on_mouse_pos)
        self.bind(state=self._on_state, pos=self._on_mouse_pos)

    def _on_mouse_pos(self, *args, override=False):
        if self.state == "down" and not override:
            return
        if self.collide_point(*self.to_widget(*Window.mouse_pos)):
            self.source = BURGER_HOVER
        else:
            self.source = BURGER_NORMAL

    def _on_state(self, *args):
        if self.state == "down":
            self.source = BURGER_PRESSED
        else:
            self._on_mouse_pos(override=True)


class ToolButton(ToggleButtonBehavior, Image):
    """Toggle buttons for tool selection."""
    def __init__(self, normal, pressed, *args, **kwargs):
        self._normal = normal
        self._pressed = pressed

        super().__init__(source=normal, size_hint=(.1, .1))

        self.group = 'tool_button'
        self.allow_no_selection = False
        self.allow_stretch = True
        self.texture.mag_filter = "nearest"

        self.bind(state=self._on_state)

    def _on_state(self, *args):
        self.source = self._pressed if self.state == "down" else self._normal
        self.texture.mag_filter = "nearest"
