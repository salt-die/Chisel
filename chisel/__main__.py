"""
SMASH ROCK!  FASTER SWING = MORE ROCK SMASHED! This app is a pre-historically accurate
representation of Paleolithic technology!  Re-invent the wheel with this (rock)cutting-edge
simulation! A caveman workout routine guaranteed to give you chiseled slabs fast!
"""
from pathlib import Path

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.garden.navigationdrawer import NavigationDrawer

from .widgets import BurgerButton, Chisel, Cursor, OptionsPanel, ToolButton


IMAGE_PATH = Path("assets", "img")
ICON = str(IMAGE_PATH / "icon.png")
TOOLS_NORMAL = tuple(str(IMAGE_PATH / "cursor" / f"up_{i}.png") for i in range(3))
TOOLS_PRESSED = tuple(str(IMAGE_PATH / "cursor" / f"selected_{i}.png") for i in range(3))
TOOLS_HOVER = tuple(str(IMAGE_PATH / "cursor" / f"down_{i}.png") for i in range(3))

class ChiselApp(App):
    def build(self):
        self.icon = ICON
        self.cursor = Cursor()
        Window.minimum_width, Window.minimum_height = Window.size
        root = FloatLayout()
        navdrawer = NavigationDrawer()
        navdrawer.toggle_state()
        navdrawer.anim_type = "slide_above_anim"

        self.chisel = chisel = Chisel()
        self.chisel_on_touch_down = chisel.on_touch_down
        self.chisel_on_touch_move = chisel.on_touch_move

        options_panel = OptionsPanel(chisel)
        navdrawer.add_widget(options_panel)

        burger = BurgerButton()
        burger.bind(on_release=navdrawer.toggle_state)

        rel_layout = RelativeLayout()
        rel_layout.add_widget(chisel)  # To push it when side panel is opened.
        navdrawer.add_widget(rel_layout)
        options_panel.build()
        options_panel.bind_to_burger(burger)
        navdrawer.bind(_anim_progress=self._set_side_panel_opacity)
        navdrawer.bind(_anim_progress=self.disable_chisel)

        tools = tuple(ToolButton(normal, pressed, hover)
                      for normal, pressed, hover in zip(TOOLS_NORMAL,
                                                        TOOLS_PRESSED,
                                                        TOOLS_HOVER))
        def set_tool(i):
            self.chisel.tool = i
            self.cursor.tool = i

        for i, tool in enumerate(tools):
            tool.bind(on_release=lambda touch:set_tool(i))

        root.add_widget(navdrawer)
        root.add_widget(burger)
        for tool in tools:
            root.add_widget(tool)

        Window.add_widget(self.cursor, canvas="after")
        return root

    def _set_side_panel_opacity(self, instance, value):
        instance.side_panel.opacity = 1 if instance._anim_progress else 0

    def disable_chisel(self, instance, value):
        if instance._anim_progress > 0:
            self.chisel.on_touch_down = self.chisel.on_touch_move = lambda *args: None
        else:
            self.chisel.on_touch_down = self.chisel_on_touch_down
            self.chisel.on_touch_move = self.chisel_on_touch_move


if __name__ == "__main__":
    ChiselApp().run()
