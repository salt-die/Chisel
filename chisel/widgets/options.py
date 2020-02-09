import contextvars
from itertools import cycle
from pathlib import Path
import webbrowser

from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.uix.image import Image
from kivy.uix.label import Label

from ..utils.i18n import DEFAULT_LOCALE, SYSTEM_LOCALE, LOCALES, TRANSLATIONS
from .mixins import RepeatingBackground
from .buttons import Button
from .popups import SelectionPopup, ImportPopup, SaveAsPopup, open_loading_popup


FONT: contextvars.ContextVar[str] = contextvars.ContextVar("font")

IMAGE_PATH = Path("assets", "img")
OPTIONS_BACKGROUND = str(IMAGE_PATH / "options_background.png")
CAVEMAN = tuple(str(IMAGE_PATH / "caveman" / f"{i}.png") for i in range(4))

GITHUB_URL = "https://github.com/salt-die/code-jam-6/tree/master/circumstantial-companions"


class OptionsPanel(RepeatingBackground, BoxLayout):
    def __init__(self, chisel):
        self.chisel = chisel
        super().__init__(orientation="vertical",
                         spacing=dp(31),
                         padding=(dp(20), dp(30), dp(20), dp(15)),
                         opacity=0)  # set opacity when side panel is opened
        self.setup_background(OPTIONS_BACKGROUND)

    def build(self, locale=SYSTEM_LOCALE):
        self.clear_widgets()
        if locale in LOCALES:
            TRANSLATIONS[locale].install()
        else:
            locale = DEFAULT_LOCALE
            TRANSLATIONS[DEFAULT_LOCALE].install()

        FONT.set(LOCALES[locale]["font"])

        title = Label(text=_("Options"),
                      font_name=FONT.get(),
                      font_size=sp(30),
                      size_hint=(1, 0.05),
                      outline_color=(0, 0, 0),
                      outline_width=2)

        default_button = dict(font_name=FONT.get(),
                              font_size=sp(18),
                              size_hint=(1, None),
                              height=dp(44))

        language_btn = Button(_("Select language"), **default_button)
        language_btn.bind(on_release=self.open_language_popup)

        import_btn = Button(_("Import..."), **default_button)
        import_btn.bind(on_release=lambda btn: ImportPopup(FONT.get(), self.chisel).open(btn))

        save_as_btn = Button(_("Save as..."), **default_button)
        save_as_btn.bind(on_release=lambda btn: SaveAsPopup(FONT.get(), self.chisel).open(btn))

        reset_btn = Button(_("Reset"), **default_button)
        reset_btn.bind(on_release=self.reset_chisel)

        src_btn = Button(_("Source code"), **default_button)
        src_btn.bind(on_release=lambda btn: webbrowser.open(GITHUB_URL))

        # Animation - Normal loading of an animation won't apply desired mag_filter to each
        # individual texture, so we load each frame and cycle through the textures 'by-hand'.
        images = []
        for source in CAVEMAN:
            image = Image(source=source, size_hint=(1, 1), allow_stretch=True)
            image.texture.mag_filter = 'nearest'
            images.append(image)
        images = cycle(images)

        animation = Image(source=CAVEMAN[0],
                          size_hint=(1, 1),
                          allow_stretch=True)
        animation.texture.mag_filter = 'nearest'

        def next_texture(*args):
            animation.texture = next(images).texture
        Clock.schedule_interval(next_texture, .2)

        widgets = [title,
                   language_btn,
                   import_btn,
                   save_as_btn,
                   reset_btn,
                   src_btn,
                   animation]

        for widget in widgets:
            self.add_widget(widget)

    def update_background(self, *args):
        # Overriden to snap to the right position.
        self.bg_rect.texture.uvsize = self._get_uvsize()
        self.bg_rect.texture = self.bg_rect.texture  # required to trigger update
        bg_width, bg_height = self._get_background_size()
        self.bg_rect.pos = self.right - bg_width, self.y
        self.bg_rect.size = bg_width, bg_height

    def open_language_popup(self, *args):
        locales = {code: info["name"] for code, info in LOCALES.items()}
        popup = SelectionPopup(_("Select language"), FONT.get(), locales)
        popup.bind(choice=lambda instance, choice: self.build(choice))
        popup.open()

    def reset_chisel(self, *args):
        popup = open_loading_popup(_("Resetting the canvas..."), FONT.get())

        def reset(dt):
            self.chisel.reset()
            popup.dismiss()
        Clock.schedule_once(reset, 0.1)

    def bind_to_burger(self, burger):
        def _reposition(*args):
            burger.pos = self.right + dp(10), self.top - burger.height - dp(10)
        self.bind(pos=_reposition, size=_reposition)
