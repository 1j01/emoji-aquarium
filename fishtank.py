#!/usr/bin/env python3

import math
import random

from rich.segment import Segment
from rich.style import Style
from textual import events
from textual.app import App, ComposeResult
from textual.color import Color
from textual.strip import Strip
from textual.widget import Widget
from textual.geometry import Offset
from textual.reactive import var

from auto_restart import restart_on_changes

tank_width = 80
tank_height = 24

# Class hierarchy for entities
class Entity:

    all_entities: list['Entity'] = []
    solid_entities: list['Entity'] = []

    def __init__(self, x, y, symbol, color=Color(255, 255, 255), bgcolor=None, solid=False):
        self.x = x
        self.y = y
        self.symbol = symbol
        self.symbol_width = 0 # calculated when rendering
        self.color = color
        self.bgcolor = bgcolor
        self.solid = solid
        self.add_to_lists()

    def add_to_lists(self):
        Entity.all_entities.append(self)
        if self.solid:
            Entity.solid_entities.append(self)
        for cls in self.__class__.mro():
            if cls is Entity:
                break
            cls.instances.append(self)

    def remove_from_lists(self):
        Entity.all_entities.remove(self)
        if self in Entity.solid_entities:
            Entity.solid_entities.remove(self)
        for cls in self.__class__.mro():
            if cls is Entity:
                break
            cls.instances.remove(self)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.instances = []

    def move(self):
        pass

    def collision_at(self, offset: Offset) -> bool:
        entities = [e for e in Entity.solid_entities if e is not self]
        if offset.y >= tank_height:
            return True
        if entity_at(offset, entities) is not None:
            return True
        if self.symbol_width > 1 and entity_at(offset + Offset(1, 0), entities) is not None:
            return True
        # Assuming there's no character wider than 2 cells
        return False

class Sinker(Entity):
    def move(self):
        if not self.collision_at(Offset(self.x, self.y + 1)):
            self.y += 1
        # In case tank shrinks, move up if we're out of bounds
        if self.y > tank_height - 1:
            self.y = tank_height - 1
        # If we're inside the ground, move up
        if self.collision_at(Offset(self.x, self.y)):
            self.y -= 1

class BottomDweller(Sinker):
    # def __init__(self, x, y, symbol, color=Color(255, 255, 255), bgcolor=None):
    #     super().__init__(x, y, symbol, color, bgcolor)
    def __init__(self, x, y):
        symbol = random.choice('🦞🐌🦐🦀🦑🐙')
        super().__init__(x, y, symbol)
        self.direction = random.choice([-1, 1])

    def move(self):
        super().move()
        # If we're on the ground, move left or right
        if self.collision_at(Offset(self.x, self.y + 1)) and random.random() < 0.3:
            if self.collision_at(Offset(self.x + self.direction, self.y)):
                if not self.collision_at(Offset(self.x + self.direction, self.y - 1)):
                    self.x += self.direction
                    self.y -= 1
                else:
                    self.direction *= -1
            else:
                self.x += self.direction
            # Randomly change direction occasionally
            if random.random() < 0.05:
                self.direction *= -1

class Fish(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, random.choice(['🐡', '🐠', '🐠', '🐟', '🐟', '🐟']))
        self.direction = random.choice([-1, 1])
        self.bubble_timer = 0

    def move(self):
        if self.collision_at(Offset(self.x + self.direction, self.y)):
            self.direction *= -1
        else:
            self.x += self.direction

        # Randomly change direction occasionally
        if random.random() < 0.05:
            self.direction *= -1

        # Create bubbles occasionally
        if self.bubble_timer <= 0 and random.random() < 0.1:
            Bubble(self.x, self.y - 1)
            self.bubble_timer = 5
        else:
            self.bubble_timer -= 1

        # Wrap around the screen
        if self.x < 0:
            self.x = tank_width
        elif self.x > tank_width:
            self.x = 0

class Ground(Entity):
    def __init__(self, x, y):
        symbol = random.choice('       .܈܉܇⋰∵⸪∴⸫˙\'⠁⠂⠄⠆⠈⠊⠌⠐⠑⠒⠔⠕⠘⠠⠡⠢⠪⡀⡁⡠⡡⡢⢀⢂')
        color = random.choice([
            Color.parse("rgb(91, 62, 31)"),
            Color.parse("rgb(139, 69, 19)"),
            Color.parse("rgb(160, 82, 45)"),
            Color.parse("rgb(205, 133, 63)"),
            Color.parse("rgb(222, 184, 135)"),
        ])
        bgcolor = random.choice([
            Color.parse("rgb(102, 67, 29)"),
            Color.parse("rgb(129, 60, 10)"),
            Color.parse("rgb(127, 79, 45)"),
            Color.parse("rgb(151, 70, 33)"),
            Color.parse("rgb(175, 107, 40)"),
        ])
        super().__init__(x, y, symbol, color, bgcolor, solid=True)

    def move(self):
        if not self.collision_at(Offset(self.x, self.y + 1)):
            self.y += 1
        # In case tank shrinks, ground will be regenerated.

class SeaUrchin(Sinker):
    def __init__(self, x, y):
        symbol = random.choice(['✶', '✷', '✸', '✹', '✺', '*', '⚹', '✳', '꘎', '💥']) # '🗯', '🦔'
        color = random.choice([
            Color.parse("rgb(255, 132, 0)"),
            Color.parse("rgb(136, 61, 194)"),
            Color.parse("rgb(255, 0, 0)"),
            Color.parse("rgb(255, 255, 255)"),
        ])
        super().__init__(x, y, symbol, color, solid=True)

class Coral(Sinker):
    def __init__(self, x, y):
        symbol = random.choice('🪸🧠') # 🫚🫁
        color = random.choice([
            Color.parse("rgb(255, 179, 0)"),
            Color.parse("rgb(255, 213, 0)"),
            Color.parse("rgb(255, 210, 254)"),
            Color.parse("rgb(255, 255, 255)"),
        ])
        super().__init__(x, y, symbol, color, solid=True)

class Shell(Sinker):
    def __init__(self, x, y):
        symbol = random.choice('🦪🐚𖡎') # 🥟
        super().__init__(x, y, symbol, solid=True)

class Rock(Sinker):
    def __init__(self, x, y):
        # rock emoji width is unreliable (it takes up one space in VS Code, but two in Ubuntu Terminal)
        # symbol = random.choice('🪨🪨🪨🪨🗿')
        symbol = random.choice('⬬⬟⭓⬢⬣☗☁⬤🗿')
        super().__init__(x, y, symbol, Color.parse("rgb(128, 128, 128)"), solid=True)

class Seaweed(Sinker):
    def __init__(self, x, y, seaweed_below=None):
        super().__init__(x, y, '🌿')
        self.seaweed_below = seaweed_below
        self.seaweed_above = None

    def move(self):
        # Apply gravity to bottom-most seaweed
        if self.seaweed_below is None:
            super().move()
        
        # Wiggle back and forth, within 1 space of the seaweed below and above
        if self.seaweed_below is not None:
            new_x = self.x + random.randint(-1, 1)
            # constrain to the range of the seaweed above
            if self.seaweed_above is not None:
                new_x = max(new_x, self.seaweed_above.x - 1)
                new_x = min(new_x, self.seaweed_above.x + 1)
            # constrain to the range of the seaweed below
            # Do this after so it takes precedence, since the bottom seaweed has gravity.
            new_x = max(new_x, self.seaweed_below.x - 1)
            new_x = min(new_x, self.seaweed_below.x + 1)
            # Constrain x so it doesn't move too much at once
            new_x = max(new_x, self.x - 1)
            new_x = min(new_x, self.x + 1)
            # Move horizontally
            self.x = new_x
            # Constrain y
            new_y = self.seaweed_below.y - 1
            new_y = min(new_y, self.y + 1)
            new_y = max(new_y, self.y - 1)
            self.y = new_y

        # Create new seaweed above if there is room
        growth_rate = 0.01
        if self.y > 0 and random.random() < growth_rate and self.seaweed_above is None:
            self.seaweed_above = Seaweed(self.x, self.y - 1, self)

class Bubble(Entity):
    def __init__(self, x, y):
        # 🫧 width is unreliable (looks wrong in Ubuntu terminal)
        symbol = random.choice(['･', '◦', '∘', 'ߋ', '𝚘', 'ᴑ', 'o', 'O', 'ₒ', '°', '˚', 'ᴼ', ':', 'ஃ', '🝆', 'ꖜ', 'ꕣ', 'ꕢ']) # , *['🫧'] * 10
        super().__init__(x, y, symbol, Color.parse("rgb(157, 229, 255)"))

    def move(self):
        self.y -= 1

        # Move sideways occasionally
        if random.random() < 0.1:
            self.x += random.choice([-1, 1])

        # Remove the bubble if it reaches the top of the tank
        if self.y < 0:
            self.remove_from_lists()

# Initialize the entities
[Fish(random.randint(0, tank_width), random.randint(0, tank_height)) for _ in range(5)]
[SeaUrchin(random.randint(0, tank_width), random.randint(0, tank_height)) for _ in range(5)]
[BottomDweller(random.randint(0, tank_width), random.randint(0, tank_height)) for _ in range(5)]
[Coral(random.randint(0, tank_width), random.randint(0, tank_height)) for _ in range(5)]
[Shell(random.randint(0, tank_width), random.randint(0, tank_height)) for _ in range(5)]
[Rock(random.randint(0, tank_width), random.randint(0, tank_height)) for _ in range(5)]
[Seaweed(random.randint(0, tank_width), random.randint(0, tank_height)) for _ in range(10)]

def ground_height(x: int) -> int:
    return 4 + int(2 * math.sin(x / 10) + 1 * math.sin(x / 5) + 1 * math.sin(x / 2))

def generate_ground():
    for ground in list(Ground.instances):
        ground.remove_from_lists()
    for x in range(tank_width):
        for y in range(tank_height-ground_height(x), tank_height):
            Ground(x, y)

generate_ground()

# Define gradient colors
light_blue = Color(135, 206, 250)
dark_blue = Color(25, 25, 112)

def entity_at(offset: Offset, entities: list[Entity]) -> Entity | None:
    for entity in entities:
        if entity.x <= offset.x < entity.x + entity.symbol_width and entity.y == offset.y:
            return entity
    return None

class Tank(Widget):

    dragging: var[Entity | None] = var[Entity | None](None)
    drag_offset: var[Offset | None] = var[Offset | None](None)

    def update(self):
        # Move entities
        dragging = app.query_one(Tank).dragging
        for entity in Entity.all_entities:
            if entity is not dragging:
                entity.move()
        # Update the screen
        self.refresh()

    def on_mount(self):
        self.set_interval(0.1, self.update)

    def render_line(self, y: int) -> Strip:
        """Render a line of the widget."""
        bg_color = light_blue.blend(dark_blue, y / self.size.height)
        bg_style = Style(bgcolor=bg_color.rich_color)
        entities_at_y = [entity for entity in Entity.all_entities if entity.y == y]
        entities_at_y.sort(key=lambda entity: entity.x)
        segments = []
        x = 0
        for entity in entities_at_y:
            # Some symbols are wider than 1 cell.
            # If there are 2-wide entities in every cell, we can only fit half of them on the screen.
            # When rendering as a strip, if we try to include every entity,
            # by default, things will get shifted rightwards,
            # since the next entity will start to the right of the last,
            # and error will accumulate as we try to fit more entities close together.

            # Hide entities that overlap instead of allowing it to shift things rightwards.
            if entity.x < x:
                continue

            # visualize segments by color (kind of unpleasant to look at,
            # at full simulation speed; maybe slow it down to debug.)
            # bg_color = light_blue.blend(dark_blue, x / self.size.width)
            # bg_style = Style(bgcolor=bg_color.rich_color)

            new_x = entity.x
            segments.append(Segment(" " * (new_x - x), bg_style, None))
            entity_style = bg_style + Style(color=entity.color.rich_color, bgcolor=entity.bgcolor.rich_color if entity.bgcolor is not None else None)
            entity_segment = Segment(entity.symbol, entity_style, None)
            segments.append(entity_segment)
            entity.symbol_width = entity_segment.cell_length
            x = new_x + entity_segment.cell_length

        segments.append(Segment(" " * (self.size.width - x), bg_style, None))
        return Strip(segments)

    def on_mouse_down(self, event: events.MouseDown) -> None:
        self.capture_mouse()
        self.dragging = entity_at(event.offset, Entity.all_entities)
        if self.dragging is not None:
            self.drag_offset = event.offset - Offset(self.dragging.x, self.dragging.y)
        else:
            Bubble(event.offset.x, event.offset.y)

    def on_mouse_up(self, event: events.MouseUp) -> None:
        self.release_mouse()
        self.dragging = None
        self.drag_offset = None

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if event.button != 1:
            return
        if self.dragging is not None:
            self.dragging.x = event.offset.x - self.drag_offset.x
            self.dragging.y = event.offset.y - self.drag_offset.y
        elif random.random() < 0.5:
            Bubble(event.offset.x, event.offset.y)

class FishTankApp(App):
    def on_resize(self, event: events.Resize) -> None:
        global tank_width, tank_height
        
        # Move everything up/down to keep things anchored relative to the bottom of the tank.
        # Do this before re-generating the ground, so that the ground doesn't get offset.
        for entity in Entity.all_entities:
            entity.y += event.size.height - tank_height
        
        tank_width = event.size.width
        tank_height = event.size.height
        
        generate_ground()

    def compose(self) -> ComposeResult:
        yield Tank()

app = FishTankApp()

# Must be before app.run() which blocks until the app exits.
# Takes the app in order to do some clean up of the app before restarting.
restart_on_changes(app)

if __name__ == "__main__":
    app.run()
