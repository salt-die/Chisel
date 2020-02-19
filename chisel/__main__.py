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
TOOLS_NORMAL = (str(IMAGE_PATH / "cursor" / f"up_{i}.png") for i in range(3))
TOOLS_SELECTED = (str(IMAGE_PATH / "cursor" / f"selected_{i}.png") for i in range(3))


class ChiselApp(App):
    def build(self):
        self.icon = ICON
        self.cursor = Cursor()
        Window.minimum_width, Window.minimum_height = Window.size
        root = FloatLayout()
        navdrawer = NavigationDrawer()
        navdrawer.toggle_state()
        navdrawer.anim_type = "slide_above_anim"

        chisel = Chisel()

        options_panel = OptionsPanel(chisel)
        navdrawer.add_widget(options_panel)

        burger = BurgerButton()
        burger.bind(on_release=navdrawer.toggle_state)

        rel_layout = RelativeLayout()  # This layout allows navdrawer to push contained widgets.
        rel_layout.add_widget(chisel)

        tools = (ToolButton(*sources) for sources in zip(TOOLS_NORMAL, TOOLS_SELECTED))
        funcs = (lambda touch: (chisel.tool(0), self.cursor.tool(0)),
                 lambda touch: (chisel.tool(1), self.cursor.tool(1)),
                 lambda touch: (chisel.tool(2), self.cursor.tool(2)))
        for i, (tool, func) in enumerate(zip(tools, funcs)):
            tool.pos_hint = {"x": i * .1 + .35, "y": .01}
            tool.bind(on_press=func)
            if not i:  # First tool button is selected.
                tool.state = "down"
            rel_layout.add_widget(tool)

        navdrawer.add_widget(rel_layout)
        options_panel.build()
        options_panel.bind_to_burger(burger)

        def on_anim(instance, value):
            instance.side_panel.opacity = chisel.disabled = 1 if instance._anim_progress else 0
        navdrawer.bind(_anim_progress=on_anim)

        root.add_widget(navdrawer)
        root.add_widget(burger)

        Window.add_widget(self.cursor, canvas="after")
        return root


if __name__ == "__main__":
    ChiselApp().run()
