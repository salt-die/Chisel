from pathlib import Path

from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.button import Button as KivyButton
from kivy.uix.popup import Popup as KivyPopup
from kivy.uix.label import Label
from kivy.properties import StringProperty
from kivy.uix.textinput import TextInput

from mixins import SignBorder
from buttons import Button

IMAGE_PATH = Path("assets", "img")
BUTTON_PRESSED = str(IMAGE_PATH / "button" / "pressed.png")
PROJECT_EXTENSION = ".chisel-project"
MAX_FILENAME_LENGTH = 128

def get_saves_path():
    path = Path.cwd()
    if (path / "saves").exists():
        return str(path / "saves")
    return str(path)


class Popup(SignBorder, KivyPopup):
    def __init__(self, title, font_name, content, **kwargs):
        super().__init__(title=title,
                         title_font=font_name,
                         title_size=sp(20),
                         title_align="center",
                         content=content,
                         separator_color=(0, 0, 0, 0),
                         background=BUTTON_PRESSED,
                         **kwargs)
        self.setup_border()


class InfoPopup(Popup):
    def __init__(self, title, text, font_name, *, dismissable=True, size_hint):
        layout = BoxLayout(orientation="vertical",
                           spacing=dp(34),
                           padding=(dp(20), dp(15)))
        self.label = Label(text=text,
                           font_name=font_name,
                           font_size=sp(20),
                           halign="center",
                           valign="middle")
        layout.add_widget(self.label)
        self.label.bind(size=self._resize_label)

        super().__init__(title,
                         font_name,
                         layout,
                         size_hint=size_hint,
                         auto_dismiss=dismissable)
        self._resize_label()

        if dismissable:
            btn = Button(_("Cancel"), font_size=sp(16), size_hint=(1, 0.35))
            layout.add_widget(btn)
            btn.bind(on_release=self.dismiss)

    def _resize_label(self, *args):
        self.label.text_size = self.label.size


def open_error_popup(text, font_name):
    popup = InfoPopup(_("An error has occured."), text, font_name, size_hint=(0.6, 0.5))
    popup.open()
    return popup


def open_loading_popup(text, font_name):
    popup = InfoPopup(_("Loading..."), text, font_name, dismissable=False, size_hint=(0.6, 0.3))
    popup.open()
    return popup


class SelectionPopup(Popup):
    choice = StringProperty()

    def __init__(self, title, font_name, choices):
        layout = BoxLayout(orientation="vertical",
                           spacing=dp(34),
                           padding=(dp(20), dp(15)))

        for key, string in choices.items():
            btn = Button(string, font_name=font_name, font_size=sp(16))

            def _make_select_function(key):
                def _select(btn):
                    self.dismiss()
                    self.choice = key
                return _select

            btn.bind(on_release=_make_select_function(key))
            layout.add_widget(btn)

        super().__init__(title, font_name, layout, size_hint=(0.5, 0.8))


class ImportPopup(Popup):
    def __init__(self, font_name, chisel):
        self.font_name = font_name
        self.chisel = chisel

        layout = BoxLayout(orientation="vertical",
                           spacing=dp(34),
                           padding=(dp(20), dp(15)))

        self.file_chooser = FileChooserListView(path=get_saves_path(),
                                                filters=[self._filter_file],
                                                size_hint=(1, 0.85))

        self.btn = Button(_("Please select a file."),
                          font_name,
                          disabled=True,
                          font_size=sp(16),
                          size_hint=(1, 0.15))

        self.file_chooser.bind(path=self._change_title, selection=self._change_btn_name)
        self.btn.bind(on_release=self._select_file)

        layout.add_widget(self.file_chooser)
        layout.add_widget(self.btn)

        super().__init__("", font_name, layout, size_hint=(0.7, 0.9))
        self._change_title()

    @staticmethod
    def _filter_file(folder, filename):
        return filename.endswith(PROJECT_EXTENSION)

    def _change_title(self, *args):
        path = self.file_chooser.path
        self.title = _("Import from {path}").format(path=path)

    def _change_btn_name(self, *args):
        selection = self.file_chooser.selection
        if selection:
            self.btn.text = _('Open "{filename}"').format(filename=Path(selection[0]).name)
            self.btn.disabled = False
        else:
            self.btn.text = _("Please select a file.")
            self.btn.disabled = True

    def _select_file(self, *args):
        selection = self.file_chooser.selection
        if selection:
            self.dismiss()
            self.loading_popup = open_loading_popup(_("Importing the project."), self.font_name)
            Clock.schedule_once(lambda dt: self._load_file(selection[0]), 0.1)

    def _load_file(self, path):
        try:
            self.chisel.load(path)
        except (ValueError, KeyError):
            open_error_popup(_("The file could not be loaded."), self.font_name)
        finally:
            self.loading_popup.dismiss()

    def on_dismiss(self, *args):
        self.file_chooser.cancel()


class SaveAsPopup(Popup):
    def __init__(self, font_name, chisel):
        self.font_name = font_name
        self.chisel = chisel
        self.save_type = None
        self.choices = {"background": ".png " + _("(with background)"),
                        "transparent": ".png " + _("(transparent)"),
                        "project": PROJECT_EXTENSION,
                        "all": _("All")}

        layout = BoxLayout(orientation="vertical",
                           spacing=dp(34),
                           padding=(dp(20), dp(15)))

        self.file_chooser = FileChooserListView(path=get_saves_path(),
                                                filters=[self._filter_file],
                                                size_hint=(1, 0.75))

        sublayout = BoxLayout(orientation="horizontal",
                              spacing=dp(10),
                              size_hint=(1, 0.1))

        self.text_input = TextInput(text="Untitled",
                                    multiline=False,
                                    font_name=font_name,
                                    font_size=sp(16),
                                    size_hint_x=0.6)

        self.save_type_btn = KivyButton(text=_("Select file type"),
                                        font_name=font_name,
                                        size_hint_x=0.4)

        sublayout.add_widget(self.text_input)
        sublayout.add_widget(self.save_type_btn)

        self.save_btn = Button(_("Please select a file type."),
                               disabled=True,
                               font_name=font_name,
                               font_size=sp(16),
                               size_hint=(1, 0.15))

        self.file_chooser.bind(path=self._change_title, selection=self._set_text)
        self.text_input.bind(text=self._on_text_input, on_text_validate=self._save_file)
        self.save_type_btn.bind(on_release=self.open_save_type_popup)
        self.save_btn.bind(on_release=self._save_file)

        for widget in (self.file_chooser, sublayout, self.save_btn):
            layout.add_widget(widget)

        super().__init__("", font_name, layout, size_hint=(0.7, 0.9))
        self._change_title()

    @staticmethod
    def _filter_file(folder, filename):
        return filename.endswith(PROJECT_EXTENSION) or filename.endswith(".png")

    def get_maybe_shortened_filename(self):
        filename = self.get_resolved_filename()
        if len(filename) > 24:
            filename, _, ext = filename.rpartition(".")
            if ext:
                return f"{filename[:6]}...{filename[-5:]}.{ext}"
            return f"{filename[:6]}...{filename[-5:]}"
        return filename

    def get_resolved_filename(self):
        filename = self.text_input.text
        ext = self._get_file_extension()
        if ext is None:
            return filename
        if not filename.endswith(ext):
            return filename + ext
        return filename

    def _change_title(self, *args):
        path = self.file_chooser.path
        self.title = _("Save to {path}").format(path=path)

    def _set_text(self, *args):
        selection = self.file_chooser.selection
        if selection:
            self.text_input.text = Path(selection[0]).name

    def _on_text_input(self, *args):
        text = self.text_input.text
        if len(text) > MAX_FILENAME_LENGTH:
            self.text_input.text = text[:MAX_FILENAME_LENGTH]
        if self.save_type:
            current_ext = self._get_file_extension()
            if current_ext == ".png" and self.text_input.text.endswith(PROJECT_EXTENSION):
                self._set_save_type(None, "project")
            elif current_ext == PROJECT_EXTENSION and self.text_input.text.endswith(".png"):
                self._set_save_type(None, "background")
        else:
            if self.text_input.text.endswith(PROJECT_EXTENSION):
                self._set_save_type(None, "project")
            elif self.text_input.text.endswith(".png"):
                self._set_save_type(None, "background")
        self._change_btn_name()

    def _change_btn_name(self, *args):
        if self.save_type is None:
            return
        filename = self.get_maybe_shortened_filename()
        self.save_btn.text = _('Save as "{filename}"').format(filename=filename)

    def _save_file(self, *args):
        try:
            self._do_saves()
        except OSError:
            open_error_popup(_("The file could not be saved due to an error "
                               "raised by the operating system.\nCommon "
                               "issue: Illegal characters in the file name."),
                             self.font_name)
        self.dismiss()

    def open_save_type_popup(self, *args):
        popup = SelectionPopup(_("Select file type"), self.font_name, self.choices)
        popup.bind(choice=self._set_save_type)
        popup.open()

    def _set_save_type(self, instance, choice):
        self.save_type_btn.text = self.choices[choice]
        self.save_btn.disabled = False
        if self.save_type is not None:
            old_ext = self._get_file_extension()
            if old_ext and self.text_input.text.endswith(old_ext):
                self.text_input.text = self.text_input.text[:-len(old_ext)]
        self.save_type = choice
        new_ext = self._get_file_extension()
        if new_ext and not self.text_input.text.endswith(new_ext):
            self.text_input.text += new_ext
        self._change_btn_name()

    def _get_file_extension(self):
        extensions = {"background": ".png",
                      "transparent": ".png",
                      "project": PROJECT_EXTENSION,
                      "all": None}
        return extensions[self.save_type]

    def _do_saves(self):
        filename = self.get_resolved_filename()
        path = Path(self.file_chooser.path)
        ext = self._get_file_extension()
        if ext is None:
            bg_path = path / (filename + ".png")
            trans_path = path / (filename + "_transparent.png")
            project_path = path / (filename + PROJECT_EXTENSION)
        else:
            bg_path = trans_path = project_path = path / filename

        def bg_func():
            self.chisel.export_png(bg_path, transparent=False)

        def trans_func():
            self.chisel.export_png(trans_path, transparent=True)

        def project_func():
            self.chisel.save(project_path)

        def all_func():
            bg_func()
            trans_func()
            project_func()

        functions = {"background": bg_func,
                     "transparent": trans_func,
                     "project": project_func,
                     "all": all_func}
        functions[self.save_type]()

    def on_dismiss(self, *args):
        self.file_chooser.cancel()