import io
from itertools import product
import json
from pathlib import Path
from random import choice

import numpy as np
from PIL import Image

from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.graphics.texture import Texture

GRAVITY = .01
FRICTION = .9

IMAGE_SCALE = .75
SCALE_INVERSE = 1 / IMAGE_SCALE
X_OFFSET = (1 - IMAGE_SCALE) / 2
Y_OFFSET = .1
IMAGE_DIM = 100, 100

RADIUS = R = 1
MIN_POWER = 1e-5
CHISEL_POWER = 1e3

BACKGROUND = str(Path("/home/salt/Documents/Python/chisel/assets", "img", "background.png"))
SOUND = tuple(str(Path("/home/salt/Documents/Python/chisel/assets",
                       'sounds', f'00{i}.wav')) for i in range(1, 5))

BOULDER_IMAGE_PATHS = tuple(Path("/home/salt/Documents/Python/chisel/assets",
                                 "img", "boulder", f"{i}.png") for i in range(5))

def perceived_brightness(colors):
    """Returns the perceived brightness of a color."""
    normalized = colors / 255
    linearized = np.where(normalized <= .04045, normalized/12.92, ((normalized + .055) / 1.055)**2.4)
    luminance = linearized @ (.2126, .7152, .0722)
    brightness = np.where(luminance <=.008856, luminance * 903.3, luminance**(1/3) * 116 - 16)
    return brightness


class Pebble:
    """
    Simple gravity physics for pebbles. Deletes itself after pebbles reach the floor.
    """

    def __init__(self, pixel, chisel, velocity):
        self.pixel = pixel
        self.chisel = chisel
        self.velocity = velocity
        self.update = Clock.schedule_interval(self.step, 1 / 30)

    def step(self, dt):
        """Gravity Physics"""
        pixel = self.pixel
        x, y = pixel.x, pixel.y
        vx, vy = self.velocity
        vx *= FRICTION
        vy *= FRICTION
        vy -= GRAVITY
        # Bounce off walls
        if not 0 < x < 1:
            vx *= -1

        self.velocity = vx, vy
        pixel.update_pos(x + vx, max(0, y + vy))

        if not pixel.y:
            self.update.cancel()
            self.chisel.canvas.remove(pixel)
            self.chisel.pebbles.remove(self) # Remove reference // kill this object


class Pixel(Rectangle):
    """
    Kivy Rectangle with unscaled coordinates (x, y) and color information.
    """

    def __init__(self, x, y, chisel, color, *args, **kwargs):
        self.x, self.y = x, y
        self.chisel = chisel
        self.color = color = Color(*color)
        a = color.a
        color.a = 0 # Initially not visible as size is not correct yet.
        super().__init__(*args, **kwargs)
        self.rescale()
        color.a = a

    def update_pos(self, x, y):
        self.x, self.y = x, y
        self.pos = x * self.chisel.width, y * self.chisel.height

    def rescale(self):
        chisel = self.chisel
        screen_w, screen_h = chisel.width, chisel.height
        image_h, image_w, _ = chisel.image.shape
        self.size = (IMAGE_SCALE * screen_w) / image_w, (IMAGE_SCALE * screen_h) / image_h


class Chisel(Widget):
    """
    Handles collision detection between pebbles and the hammer.  Creates Pebbles on collision.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tool = 0  # 0, 1, or 2
        self.sounds = tuple(SoundLoader.load(sound) for sound in SOUND)
        self.load_boulder()
        self.setup_canvas()
        self.bind(size=self.resize, pos=self.resize)

    def load_boulder(self, path_to_image=None):
        if path_to_image is None:
            image = Image.open(choice(BOULDER_IMAGE_PATHS))
            image.thumbnail(IMAGE_DIM, Image.NEAREST)
            w, h = image.size
            image = np.frombuffer(image.tobytes(), dtype=np.uint8)
            self.image = image.reshape((h, w, 4))[::-1, :, :].copy()

            alpha_channel = self.image[:, :, -1] # Fix some slightly transparent pixels
            alpha_channel[alpha_channel > 127] = 255
        else:
            self.image = np.load(path_to_image)
            h, w, _ = self.image.shape

        self.texture = Texture.create(size=(w, h))
        self.texture.mag_filter = 'nearest'
        self.texture.blit_buffer(self.image.tobytes(), colorfmt='rgba', bufferfmt='ubyte')

    def setup_canvas(self):
        self.pebbles = [] # Any falling pebbles will be destroyed.

        with self.canvas:
            self.background_color = Color(1, 1, 1, 1)
            self.background = Rectangle(source=BACKGROUND)
            self.background.texture.mag_filter = 'nearest'

            self.boulder = Rectangle(texture=self.texture)

    def resize(self, *args):
        self.background.pos = self.pos
        self.background.size = self.size

        self.boulder.size = IMAGE_SCALE * self.width, IMAGE_SCALE * self.height
        self.boulder.pos = self.width * X_OFFSET, self.height * Y_OFFSET

        for pebble in self.pebbles:
            pebble.pixel.rescale()

    def tool(self, i):
        self._tool = i

    def poke_power(self, touch, pixel_x, pixel_y):
        """
        Returns the force vector of a poke.
        """
        tx, ty = touch.spos
        dx, dy = pixel_x - tx, pixel_y - ty
        distance = max(.001, dx**2 + dy**2)

        tdx, tdy = touch.dsx, touch.dsy
        touch_velocity = tdx**2 + tdy**2

        power = max(CHISEL_POWER * touch_velocity, MIN_POWER) / distance
        return power * dx, power * dy

    def poke(self, touch):
        tx, ty = touch.spos
        x, y = SCALE_INVERSE * (tx - X_OFFSET), SCALE_INVERSE * (ty - Y_OFFSET)
        if not (0 <= x <= 1 and 0 <= y <= 1):
            return

        image = self.image
        h, w, _ = image.shape
        x, y = int(x * w), int(y * h) # Image coordinate of pixel in center of poke
        # poke bounds; R is poke radius
        l, r = max(0, x - R),  min(w, x + R + 1) # left and right bounds
        t, b = max(0, y - R),  min(h, y + R + 1) # top and bottom bounds

        # Create pebbles around poke and darken area:
        for x, y in product(range(l, r), range(t, b)):
            color = image[y, x, :]
            if not color[-1] or perceived_brightness(color[:-1]) < 30 * self._tool:
                continue

            px, py = x * IMAGE_SCALE / w + X_OFFSET, y * IMAGE_SCALE / h + Y_OFFSET
            with self.canvas:
                pixel = Pixel(px, py, self, color / 255)
            velocity = self.poke_power(touch, px, py)
            self.pebbles.append(Pebble(pixel, self, velocity))

            darker = color[:-1] * .8
            if perceived_brightness(darker) < 20:
                image[y, x, -1] = 0
            else:
                image[y, x, :-1] = darker

        self.texture.blit_buffer(image.tobytes(), colorfmt='rgba', bufferfmt='ubyte')
        self.canvas.ask_update()

    def on_touch_down(self, touch):
        self.poke(touch)
        choice(self.sounds).play()
        return True

    def on_touch_move(self, touch):
        self.poke(touch)
        return True

    def reset(self):
        self.load_boulder()
        self.canvas.clear()
        self.setup_canvas()

    def save(self, path_to_file):
        buffer = io.BytesIO() # Numpy will overwrite the extension unless we save to a buffer.
        np.save(buffer, self.image, fix_imports=False)

        with open(path_to_file, 'w') as file:
            file.write(buffer.getvalue())

    def load(self, path_to_file):
        self.load_boulder(path_to_file)
        self.canvas.clear()
        self.setup_canvas()

    def export_png(self, path_to_file, transparent=False):
        if transparent:
            self.background_color.a = 0

        buffer = io.BytesIO()  # Kivy hides filename errors, so we export to buffer first.
        self.export_as_image().save(buffer, fmt="png")

        with open(path_to_file, "wb") as file:
            file.write(buffer.getvalue())

        self.background_color.a = 1


if __name__ == '__main__':
    class ChiselApp(App):
        def build(self):
            return Chisel()
    ChiselApp().run()
