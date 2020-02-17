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

GRAVITY = .02
FRICTION = .9
DISLODGE_VELOCITY = 1e-3
MAX_VELOCITY = .2

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

def is_dislodged(velocity):
    """
    Return False if velocity isn't enough to dislodge a pebble, else return the clipped
    velocity vector.
    """
    x, y = velocity
    magnitude = (x**2 + y**2)**.5
    if magnitude < DISLODGE_VELOCITY:
        return False
    if magnitude > MAX_VELOCITY:
        x *= MAX_VELOCITY / magnitude
        y *= MAX_VELOCITY / magnitude
    return x, y


class Pebble:
    """
    This handles physics for dislodged pebbles. Deletes itself after pebbles reach the floor.
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
        pixel.x, pixel.y = x + vx, max(0, y + vy)
        chisel = self.chisel
        pixel.rescale(chisel.width, chisel.height)

        if not pixel.y:
            self.update.cancel()
            chisel.canvas.remove(pixel)
            chisel.pebbles.remove(self) # Remove reference // kill this object


class Pixel(Rectangle):
    """
    Kivy Rectangle with unscaled coordinates (x, y) and color information.
    """

    def __init__(self, x, y, color, *args, **kwargs):
        self.x = x
        self.y = y
        self.color = Color(*color)
        self.a = self.color.a
        self.color.a = 0 # Initially not visible as size is not correct yet.
        super().__init__(*args, **kwargs)

    def rescale(self, screen_width, screen_height):
        self.color.a = self.a # Visible after rescale
        self.pos = self.x * screen_width, self.y * screen_height
        w, h = IMAGE_DIM
        self.size = (IMAGE_SCALE * screen_width) / w, (IMAGE_SCALE * screen_height) / h


class Chisel(Widget):
    """
    Handles collision detection between pebbles and the hammer.  Creates Pebbles on collision.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tool = 0  # 0, 1, or 2
        self.sounds = tuple(SoundLoader.load(sound) for sound in SOUND)
        self.setup_canvas()
        self.bind(size=self.resize, pos=self.resize)

    def setup_canvas(self):
        self.pebbles = [] # Any falling pebbles will be destroyed.

        image = Image.open(choice(BOULDER_IMAGE_PATHS))
        image.thumbnail(IMAGE_DIM, Image.NEAREST)
        w, h = image.size
        image = np.frombuffer(image.tobytes(), dtype=np.uint8)
        self.image = image.reshape((h, w, 4))[::-1, :, :].copy()

        alpha_channel = self.image[:, :, -1] # Fix some slightly transparent pixels
        alpha_channel[alpha_channel > 127] = 255

        self.texture = Texture.create(size=(w, h))
        self.texture.mag_filter = 'nearest'
        self.texture.blit_buffer(self.image.tobytes(), colorfmt='rgba', bufferfmt='ubyte')

        with self.canvas:
            self.background_color = Color(1, 1, 1, 1)
            self.background = Rectangle(source=BACKGROUND)
            self.background.texture.mag_filter = 'nearest'

            self.rect = Rectangle(texture=self.texture)

    def resize(self, *args):
        self.background.pos = self.pos
        self.background.size = self.size
        self.rect.size = IMAGE_SCALE * self.width, IMAGE_SCALE * self.height
        self.rect.pos = self.width * X_OFFSET, self.height * Y_OFFSET

    def tool(self, i):
        self._tool = i

    def poke_power(self, touch, pebble_x, pebble_y):
        """
        Returns the force vector of a poke.
        """
        tx, ty = touch.spos
        dx, dy = pebble_x - tx, pebble_y - ty
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
        l, r = max(0, x - R),  min(w - 1, x + R + 1) # left and right bounds
        t, b = max(0, y - R),  min(h - 1, y + R + 1) # top and bottom bounds

        # Create pebbles around poke:
        for x, y in product(range(l, r), range(t, b)):
            color = image[y, x, :]
            if not color[-1]: # If color is transparent do nothing.
                continue

            px, py = x * IMAGE_SCALE / w + X_OFFSET, y * IMAGE_SCALE / h + Y_OFFSET
            with self.canvas:
                pixel = Pixel(px, py, color / 255)
            velocity = self.poke_power(touch, px, py)
            self.pebbles.append(Pebble(pixel, self, velocity))

        # Darken poked area:
        view = image[t:b, l:r, :-1]
        image[t:b, l:r, :-1] = view * .8
        mask = view[:, :, :-1].sum(axis=2) < 100 # If color is sufficiently dark...
        image[t:b, l:r, -1][mask] = 0 # ...then set alpha to 0.

        self.texture.blit_buffer(image.tobytes(), colorfmt='rgba', bufferfmt='ubyte')
        self.canvas.ask_update()

    def on_touch_down(self, touch):
        self.poke(touch)
        choice(self.sounds).play()
        return True

    def on_touch_move(self, touch):
        self.poke(touch)
        return True

if __name__ == '__main__':
    class ChiselApp(App):
        def build(self):
            return Chisel()
    ChiselApp().run()
