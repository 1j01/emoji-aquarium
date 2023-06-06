#!/usr/bin/env python3

import math
import os
import sys
import psutil
import random

from watchdog.events import PatternMatchingEventHandler, FileSystemEvent, EVENT_TYPE_CLOSED, EVENT_TYPE_OPENED
from watchdog.observers import Observer
from rich.segment import Segment
from rich.style import Style
from textual import events
from textual.app import App, ComposeResult
from textual.color import Color
from textual.strip import Strip
from textual.widget import Widget
from textual.geometry import Offset
from textual.reactive import var

def restart_program():
    """Restarts the current program, after resetting terminal state, and cleaning up file objects and descriptors."""

    try:
        app.exit()
        # It's meant to eventually call this, but we need it immediately (unless we delay with asyncio perhaps)
        # Otherwise the terminal will be left in a state where you can't (visibly) type anything
        # if you exit the app after reloading, since the new process will pick up the old terminal state.
        app._driver.stop_application_mode()
    except Exception as e:
        print("Error stopping application mode. The command line may not work as expected. The `reset` command should restore it on Linux.", e)

    try:
        try:
            if observer:
                observer.stop()
                observer.join(timeout=1)
                if observer.is_alive():
                    print("Timed out waiting for file change observer thread to stop.")
        except RuntimeError as e:
            # Ignore "cannot join current thread" error
            # join() might be redundant, but I'm keeping it just in case something with threading changes in the future
            if str(e) != "cannot join current thread":
                raise
    except Exception as e:
        print("Error stopping file change observer:", e)

    try:
        p = psutil.Process(os.getpid())
        for handler in p.open_files() + p.connections():
            try:
                os.close(handler.fd)
            except Exception as e:
                print(f"Error closing file descriptor ({handler.fd}):", e)
    except Exception as e:
        print("Error closing file descriptors:", e)

    os.execl(sys.executable, *sys.orig_argv)

class RestartHandler(PatternMatchingEventHandler):
    """A handler for file changes"""
    def on_any_event(self, event: FileSystemEvent):
        if event.event_type in (EVENT_TYPE_CLOSED, EVENT_TYPE_OPENED):
            # These seem like they'd just cause trouble... they're not changes, are they?
            return
        print("Reloading due to FS change:", event.event_type, event.src_path)
        restart_program()

def restart_on_changes():
    """Restarts the current program when a file is changed"""
    global observer
    observer = Observer()
    handler = RestartHandler(
        # Don't need to restart on changes to .css, since Textual will reload them in --dev mode.
        # WET: WatchDog doesn't match zero directories for **, so we have to split up any patterns that use it.
        patterns=[
            "**/*.py", "*.py"
        ],
        ignore_patterns=[
            ".history/**/*", ".history/*",
            ".vscode/**/*", ".vscode/*",
            ".git/**/*", ".git/*",
            "node_modules/**/*", "node_modules/*",
            "__pycache__/**/*", "__pycache__/*",
            "venv/**/*", "venv/*",
        ],
        ignore_directories=True,
    )
    observer.schedule(handler, path='.', recursive=True)
    observer.start()


tank_width = 80
tank_height = 24

# Class hierarchy for entities
class Entity:
    def __init__(self, x, y, symbol, color=Color(255, 255, 255), bgcolor=None):
        self.x = x
        self.y = y
        self.symbol = symbol
        self.symbol_width = 0 # calculated when rendering
        self.color = color
        self.bgcolor = bgcolor

    def move(self):
        pass

    def collision_at(self, offset: Offset) -> bool:
        entities = [e for e in solid_entities() if e is not self]
        return offset.y >= tank_height or entity_at(offset, entities) is not None


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
            self.x = tank_width
        elif self.x > tank_width:
            self.x = 0

class Ground(Entity):
    def __init__(self, x, y):
        symbol = random.choice('       ⠁⠂⠃⠄⠅⠆⠇⠈⠉⠊⠋⠌⠍⠎⠏⠐⠑⠒⠓⠔⠕⠖⠗⠘⠙⠚⠛⠜⠝⠞⠟⠠⠡⠢⠣⠤⠥⠦⠧⠨⠩⠪⠫⠬⠭⠮⠯⠰⠱⠲⠳⠴⠵⠶⠷⠸⠹⠺⠻⠼⠽⠾⠿⡀⡁⡂⡃⡄⡅⡆⡇⡈⡉⡊⡋⡌⡍⡎⡏⡐⡑⡒⡓⡔⡕⡖⡗⡘⡙⡚⡛⡜⡝⡞⡟⡠⡡⡢⡣⡤⡥⡦⡧⡨⡩⡪⡫⡬⡭⡮⡯⡰⡱⡲⡳⡴⡵⡶⡷⡸⡹⡺⡻⡼⡽⡾⡿⢀⢁⢂⢃⢄⢅⢆⢇⢈⢉⢊⢋⢌⢍⢎⢏⢐⢑⢒⢓⢔⢕⢖⢗⢘⢙⢚⢛⢜⢝⢞⢟⢠⢡⢢⢣⢤⢥⢦⢧⢨⢩⢪⢫⢬⢭⢮⢯⢰⢱⢲⢳⢴⢵⢶⢷⢸⢹⢺⢻⢼⢽⢾⢿⣀⣁⣂⣃⣄⣅⣆⣇⣈⣉⣊⣋⣌⣍⣎⣏⣐⣑⣒⣓⣔⣕⣖⣗⣘⣙⣚⣛⣜⣝⣞⣟⣠⣡⣢⣣⣤⣥⣦⣧⣨⣩⣪⣫⣬⣭⣮⣯⣰⣱⣲⣳⣴⣵⣶⣷⣸⣹⣺⣻⣼⣽⣾⣿')
        color = random.choice([
            Color.parse("rgb(91, 62, 31)"),
            Color.parse("rgb(139, 69, 19)"),
            Color.parse("rgb(160, 82, 45)"),
            Color.parse("rgb(205, 133, 63)"),
            Color.parse("rgb(222, 184, 135)"),
        ])
        super().__init__(x, y, symbol, color, Color.parse("rgb(43, 25, 22)"))

    def move(self):
        if not self.collision_at(Offset(self.x, self.y + 1)):
            self.y += 1
        # In case tank shrinks, ground will be regenerated.

class SeaUrchin(Entity):
    def __init__(self, x, y):
        symbol = random.choice(['✶', '✷', '✸', '✹', '✺', '*', '⚹', '✳', '꘎', '💥']) # '🗯', '🦔'
        color = random.choice([
            Color.parse("rgb(255, 132, 0)"),
            Color.parse("rgb(136, 61, 194)"),
            Color.parse("rgb(255, 0, 0)"),
            Color.parse("rgb(255, 255, 255)"),
        ])
        super().__init__(x, y, symbol, color)

    def move(self):
        if not self.collision_at(Offset(self.x, self.y + 1)):
            self.y += 1
        # In case tank shrinks, move up if we're out of bounds
        if self.y > tank_height - 1:
            self.y = tank_height - 1

class Seaweed(Entity):
    def __init__(self, x, y, seaweed_below=None):
        super().__init__(x, y, '🌿')
        self.seaweed_below = seaweed_below
        self.seaweed_above = None

    def move(self):
        # Apply gravity to bottom-most seaweed
        if self.seaweed_below is None:
            if not self.collision_at(Offset(self.x, self.y + 1)):
                self.y += 1
            # In case tank shrinks, move up if we're out of bounds
            if self.y > tank_height - 1:
                self.y = tank_height - 1
            # If we're inside the ground, move up
            if self.collision_at(Offset(self.x, self.y)):
                self.y -= 1
        
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
            new_seaweed = Seaweed(self.x, self.y - 1, self)
            seaweed.append(new_seaweed)
            self.seaweed_above = new_seaweed

class Bubble(Entity):
    def __init__(self, x, y):
        symbol = random.choice(['･', '◦', '∘', 'ߋ', '𝚘', 'ᴑ', 'o', 'O', 'ₒ', '°', '˚', 'ᴼ', ':', 'ஃ', '🝆', 'ꖜ', 'ꕣ', 'ꕢ', *['🫧'] * 10])
        super().__init__(x, y, symbol, Color.parse("rgb(157, 229, 255)"))

    def move(self):
        self.y -= 1

        # Move sideways occasionally
        if random.random() < 0.1:
            self.x += random.choice([-1, 1])

        # Remove the bubble if it reaches the top of the tank
        if self.y < 0:
            bubbles.remove(self)

# Initialize the entities
fish = [Fish(random.randint(0, tank_width), random.randint(0, tank_height)) for _ in range(5)]
sea_urchins = [SeaUrchin(random.randint(0, tank_width), random.randint(0, tank_height)) for _ in range(5)]
seaweed = [Seaweed(random.randint(0, tank_width), random.randint(0, tank_height)) for _ in range(10)]
bubbles = []
ground = []

def ground_height(x: int) -> int:
    return int(math.sin(x / 10) * 2 + 3)

def generate_ground():
    ground.clear()
    for x in range(tank_width):
        for y in range(tank_height-ground_height(x), tank_height):
            ground.append(Ground(x, y))

generate_ground()

# Define gradient colors
light_blue = Color(135, 206, 250)
dark_blue = Color(25, 25, 112)

def all_entities():
    return fish + sea_urchins + seaweed + bubbles + ground

def solid_entities():
    return ground + sea_urchins

def entity_at(offset: Offset, entities: list[Entity]) -> Entity | None:
    for entity in entities:
        if entity.x <= offset.x < entity.x + entity.symbol_width and entity.y == offset.y:
            return entity
    return None

def step():
    # Move entities
    dragging = app.query_one(Tank).dragging
    for entity in all_entities():
        if entity is not dragging:
            entity.move()

class Tank(Widget):

    dragging: var[Entity | None] = var(None)
    drag_offset: var[Offset | None] = var(None)

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
            entity_style = bg_style + Style(color=entity.color.rich_color, bgcolor=entity.bgcolor.rich_color if entity.bgcolor is not None else None)
            entity_segment = Segment(entity.symbol, entity_style, None)
            segments.append(entity_segment)
            entity.symbol_width = entity_segment.cell_length
            x = new_x + entity_segment.cell_length

        segments.append(Segment(" " * (self.size.width - x), bg_style, None))
        return Strip(segments)

    def on_mouse_down(self, event: events.MouseDown) -> None:
        self.capture_mouse()
        self.dragging = entity_at(event.offset, all_entities())
        if self.dragging is not None:
            self.drag_offset = event.offset - Offset(self.dragging.x, self.dragging.y)
        else:
            bubbles.append(Bubble(event.offset.x, event.offset.y))

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
            bubbles.append(Bubble(event.offset.x, event.offset.y))

class FishTankApp(App):
    def update(self):
        step()
        self.query_one(Tank).refresh()

    def on_mount(self):
        self.set_interval(0.1, self.update)

    def on_resize(self, event: events.Resize) -> None:
        global tank_width, tank_height
        tank_width = event.size.width
        tank_height = event.size.height
        generate_ground()

    def compose(self) -> ComposeResult:
        yield Tank()

app = FishTankApp()

restart_on_changes() # must be before app.run() which blocks until the app exits

if __name__ == "__main__":
    app.run()
