#!/usr/bin/env python3
import random
from rich.segment import Segment
from rich.style import Style
from textual.app import App, ComposeResult
from textual.color import Color
from textual.strip import Strip
from textual.widget import Widget

# Class hierarchy for entities
class Entity:
    def __init__(self, x, y, symbol, color=Color(255, 255, 255)):
        self.x = x
        self.y = y
        self.symbol = symbol
        self.color = color

    def move(self):
        pass

class Fish(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, random.choice(['🐡', '🐠', '🐠', '🐟', '🐟', '🐟']))
        self.direction = random.choice([-1, 1])
        self.bubble_timer = 0

    def move(self):
        self.x += self.direction

        # Randomly change direction occasionally
        if random.random() < 0.05:
            self.direction *= -1

        # Create bubbles occasionally
        if self.bubble_timer <= 0 and random.random() < 0.1:
            bubbles.append(Bubble(self.x, self.y - 1))
            self.bubble_timer = 5
        else:
            self.bubble_timer -= 1

        # Wrap around the screen
        if self.x < 0:
            self.x = 79
        elif self.x > 79:
            self.x = 0

class SeaUrchin(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, random.choice(['✶', '✷', '✸', '✹', '✺', '*', '🦔']))

    def move(self):
        self.y += 1

        # Wrap around the screen
        if self.y > 23:
            self.y = 0

class Seaweed(Entity):
    def __init__(self, x, y, seaweed_below=None):
        super().__init__(x, y, '🌿')
        self.seaweed_below = seaweed_below
        self.seaweed_above = None

    def move(self):
        # Wiggle back and forth, within 1 space of the seaweed below and above
        if self.seaweed_below is not None:
            new_x = self.x + random.randint(-1, 1)
            # constrain to the range of the seaweed below
            new_x = max(new_x, self.seaweed_below.x - 1)
            new_x = min(new_x, self.seaweed_below.x + 1)
            # constrain to the range of the seaweed above
            if self.seaweed_above is not None:
                new_x = max(new_x, self.seaweed_above.x - 1)
                new_x = min(new_x, self.seaweed_above.x + 1)
            self.x = new_x

        # Create new seaweed above if there is room
        growth_rate = 0.01
        if self.y > 0 and random.random() < growth_rate and self.seaweed_above is None:
            new_seaweed = Seaweed(self.x, self.y - 1, self)
            seaweed.append(new_seaweed)
            self.seaweed_above = new_seaweed

class Bubble(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, '🫧')

    def move(self):
        self.y -= 1

        # Remove the bubble if it reaches the top of the tank
        if self.y < 0:
            bubbles.remove(self)

# Initialize the entities
fish = [Fish(random.randint(0, 79), random.randint(0, 23)) for _ in range(5)]
sea_urchins = [SeaUrchin(random.randint(0, 79), random.randint(0, 23)) for _ in range(5)]
seaweed = [Seaweed(random.randint(0, 79), random.randint(0, 23)) for _ in range(10)]
bubbles = []

# Define gradient colors
light_blue = Color(135, 206, 250)
dark_blue = Color(25, 25, 112)

def all_entities():
    return fish + sea_urchins + seaweed + bubbles

def step():
    # Move entities
    for entity in all_entities():
        entity.move()

class Tank(Widget):
    def render_line(self, y: int) -> Strip:
        """Render a line of the widget."""
        bg_color = light_blue.blend(dark_blue, y / self.size.height)
        bg_style = Style(bgcolor=bg_color.rich_color)
        entities_at_y = [entity for entity in all_entities() if entity.y == y]
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
            entity_segment = Segment(entity.symbol, bg_style, None)
            segments.append(entity_segment)
            x = new_x + entity_segment.cell_length

        segments.append(Segment(" " * (self.size.width - x), bg_style, None))
        return Strip(segments)

class FishTankApp(App):
    def update(self):
        step()
        self.query_one(Tank).refresh()

    def on_mount(self):
        self.set_interval(0.1, self.update)

    def compose(self) -> ComposeResult:
        yield Tank()

app = FishTankApp()

if __name__ == "__main__":
    app.run()
