#!/usr/bin/env python3

import math
import random
from abc import ABC, abstractmethod
import time
from typing import Type

from rich.segment import Segment
from rich.style import Style
from textual import events
from textual.app import App, ComposeResult
from textual.color import Color
from textual.geometry import Offset
from textual.reactive import var
from textual.strip import Strip
from textual.widget import Widget

from auto_restart import restart_on_changes

tank_width = 80
tank_height = 24

# Class hierarchy for entities
class Entity(ABC):

    instances: list['Entity'] = []
    """All instances of this class. This is available on each subclass."""
    solid_instances: list['Entity'] = []
    """All instances of this class that are solid. This is available on each subclass."""

    def __init__(self, x: int, y: int, symbol: str, color: Color = Color(255, 255, 255), bgcolor: Color | None = None, solid: bool = False):
        self.x = x
        self.y = y
        self.symbol = symbol
        self.symbol_width = 0 # calculated when rendering
        self.color = color
        self.bgcolor = bgcolor
        self.solid = solid
        self.add_to_lists()

    def add_to_lists(self):
        for cls in self.__class__.mro():
            if issubclass(cls, Entity):
                cls.instances.append(self)
                if self.solid:
                    cls.solid_instances.append(self)
                if cls is Entity:
                    break

    def remove_from_lists(self):
        for cls in self.__class__.mro():
            if issubclass(cls, Entity):
                if self in cls.instances:
                    cls.instances.remove(self)
                if self in cls.solid_instances:
                    cls.solid_instances.remove(self)
                if cls is Entity:
                    break

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.instances = []
        cls.solid_instances = []

    @abstractmethod
    def move(self):
        pass

    def collision_at(self, offset: Offset) -> bool:
        entities = [e for e in Entity.solid_instances if e is not self]
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
    def __init__(self, x, y, symbol = None):
        if symbol is None:
            symbol = random.choice('🦞🐌🦐🦀')
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

class Ink(Entity):
    def __init__(self, x, y, color, opacity=1.0):
        super().__init__(x, y, '▓', color)
        self.opaque_color = color
        self.opacity = opacity

    def move(self):
        self.color = self.opaque_color.with_alpha(self.opacity)
        self.opacity -= 0.01
        if self.opacity <= 0:
            self.remove_from_lists()
        # Spread out
        if self.opacity > 0.3:
            for offset in [Offset(0, 1), Offset(0, -1), Offset(1, 0), Offset(-1, 0)]:
                spread_pos = Offset(self.x, self.y) + offset
                # if entity_at(spread_pos, Ink.instances) is None:
                if entity_at(spread_pos, Entity.instances) is None:
                    Ink(spread_pos.x, spread_pos.y, self.opaque_color, self.opacity - 0.3)

class Cephalopod(BottomDweller):
    def __init__(self, x, y):
        symbol = random.choice('🦑🐙')
        super().__init__(x, y, symbol)
        self.ink_color = Color.parse("rgb(0, 0, 0)") if symbol == '🐙' else Color.parse("rgb(0, 0, 100)")
        self.ink_timer = 0
        self.hunting = None
        self.scared = False

    def move(self):
        super().move()
        # Look for predators
        def distance(entity: Entity) -> float:
            return math.sqrt((entity.x - self.x) ** 2 + (entity.y - self.y) ** 2)
        nearby = sorted(Entity.instances, key=distance)
        nearby = [entity for entity in nearby if distance(entity) < 5]
        if random.random() < 0.1:
            for entity in nearby:
                if self.is_predator(entity):
                    self.ink()
                    self.scared = True
                    # Run away
                    self.hunting = None
                    if entity.x < self.x:
                        self.direction = 1
                    elif entity.x > self.x:
                        self.direction = -1
                    break
        # Look for prey
        if random.random() < 0.1:
            for entity in nearby:
                if self.is_prey(entity):
                    self.hunting = entity
                    break
        # Move towards prey
        if self.hunting is not None:
            if self.hunting.x < self.x:
                self.direction = -1
            elif self.hunting.x > self.x:
                self.direction = 1
            else:
                self.direction = random.choice([-1, 1])
            if self.collision_at(Offset(self.x + self.direction, self.y)):
                self.hunting = None
            else:
                self.x += self.direction
        # Eat prey
        if self.hunting is not None and self.hunting.x == self.x and self.hunting.y == self.y:
            self.hunting.remove_from_lists()
            self.hunting = None

    def is_predator(self, entity: Entity) -> bool:
        if entity == self:
            return False
        if isinstance(entity, Cephalopod):
            return True
        if entity.symbol in "🦈🐊🐉🐲🐳🐋🐙🦑🐧🦭🦦":
            return True
        return False

    def is_prey(self, entity: Entity) -> bool:
        if entity == self:
            return False
        return entity.symbol in "🐟🐠🦐🦀🦞🐙🦑🦪🐌🪼🍤🍣"

    def ink(self):
        Ink(self.x, self.y, self.ink_color)

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
        symbol = random.choice('       ࿔𖡎.܈܉܇⋰∵⸪∴⸫˙\'⠁⠂⠄⠆⠈⠊⠌⠐⠑⠒⠔⠕⠘⠠⠡⠢⠪⡀⡁⡠⡡⡢⢀⢂')
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

class HumanBodyPart(Entity):
    def __init__(self, x: int, y: int, symbol: str, human: 'Human'):
        super().__init__(x, y, symbol, Color.parse("rgb(255, 255, 0)"), solid=False)
        self.human = human
    def move(self):
        pass
class HumanHead(HumanBodyPart):
    pass
class HumanTorso(HumanBodyPart):
    pass
class HumanLeftArm(HumanBodyPart):
    pass
class HumanRightArm(HumanBodyPart):
    pass
class HumanLeftLeg(HumanBodyPart):
    pass
class HumanRightLeg(HumanBodyPart):
    pass

class Human(Entity):
    """
    Human divers use several symbols in a template, with entities for each body part.

    Some of these examples vary from the template, and include extra parts for gear or legs.
      🤿
    🫷🧥🫸
      👖
     🩴🩴

     ➿🏒
    /👙\
     /\

      |
    🧯🥽
    💪🩱🫳
    🦵 🦶

       |
      ꝏ    ∞ ಹ  ⛽🛢️
    👋🎽🖖
      🩳
      🧦
    """
    def __init__(self, x: int, y: int):
        super().__init__(x, y, '', Color.parse("rgb(255, 255, 0)"))
        self.direction = random.choice([-1, 0, 1])
        self.vertical_direction = random.choice([-1, 0, 1])
        self.vertical_move_timer = 0
        self.bubble_timer = 0
        self.attention: Entity | None = None
        self.seen: set[Entity] = set()
        TEMPLATE: list[list[Type[HumanBodyPart] | None]] = [
            [None, None, HumanHead, None, None],
            [HumanLeftArm, None, HumanTorso, None, HumanRightArm],
            [None, HumanLeftLeg, None, HumanRightLeg, None],
        ]
        self.parts: dict[Offset, HumanBodyPart] = {}
        for row in range(len(TEMPLATE)):
            for col in range(len(TEMPLATE[row])):
                cls = TEMPLATE[row][col]
                if cls is not None:
                    if cls is HumanHead:
                        part_symbol = random.choice('🤿🥽➿ꝏ∞ಹ😎')
                    elif cls is HumanTorso:
                        part_symbol = random.choice('🧥🩱👙🎽')
                    elif cls is HumanLeftArm:
                        part_symbol = random.choice('🫷💪🖖👋')
                    elif cls is HumanRightArm:
                        part_symbol = random.choice('🫸🫳🖖👋')
                    # elif cls is HumanLeftLeg or cls is HumanRightLeg:
                    #     part_symbol = "🩴"
                    elif cls is HumanLeftLeg:
                        part_symbol = random.choice('🦵')
                    elif cls is HumanRightLeg:
                        part_symbol = random.choice('🦶')
                    else:
                        raise Exception(f"Unknown class for human body part: {cls}")

                    offset = Offset(col - 2, row)
                    part = cls(self.x + offset.x, self.y + offset.y, part_symbol, self)
                    self.parts[offset] = part

    def move(self):
        if self.collision_at(Offset(self.x + self.direction, self.y)):
            self.direction *= -1
        else:
            self.x += self.direction
        if self.vertical_direction != 0:
            self.vertical_move_timer -= 1
            if self.vertical_move_timer <= 0:
                self.vertical_move_timer = 10
                if self.collision_at(Offset(self.x, self.y + self.vertical_direction)):
                    self.vertical_direction = 0
                else:
                    self.y += self.vertical_direction

        # Randomly change direction occasionally
        if random.random() < 0.05:
            self.direction = random.choice([-1, 0, 1])
        if random.random() < 0.05:
            self.vertical_direction = random.choice([-1, 0, 1])

        # Create bubbles regularly, in bursts
        if self.bubble_timer <= 6:
            Bubble(self.x, self.y - 1)
        if self.bubble_timer <= 0:
            self.bubble_timer = 20
        else:
            self.bubble_timer -= 1

        # Wrap around the screen
        if self.x < 0:
            self.x = tank_width - 1
        elif self.x > tank_width - 1:
            self.x = 0

        # Look around
        if random.random() < 0.05:
            self.attention = None
            def distance(entity: Entity) -> float:
                return math.sqrt((entity.x - self.x) ** 2 + (entity.y - self.y) ** 2)
            nearby = sorted(Entity.instances, key=distance)
            nearby = [entity for entity in nearby if distance(entity) < 5]
            for entity in nearby:
                if entity not in self.seen and self.finds_interesting(entity):
                    self.seen.add(entity)
                    self.attention = entity
                    self.direction = 0
                    self.vertical_direction = 0
                    # Debug: visualize attention (persisting after attention is lost)
                    # entity.bgcolor = Color.parse("rgb(255, 0, 0)")
                    break

        # Position body parts
        self.position_subparts()

        # Get outside ground if spawned inside it or moved into it
        for offset in self.parts.keys():
            if entity_at(Offset(self.x + offset.x, self.y + offset.y), Ground.instances) is not None:
                self.y -= 1
                break

    def finds_interesting(self, entity: Entity) -> bool:
        if entity == self:
            return False
        if isinstance(entity, Human):
            return False
        if isinstance(entity, HumanBodyPart):
            return False
        if isinstance(entity, Bubble):
            return False
        if isinstance(entity, Ink):
            return False
        if isinstance(entity, Shell):
            return False
        if isinstance(entity, Rock):
            return False
        if isinstance(entity, Seaweed):
            return False
        if isinstance(entity, Ground):
            return False
        # if isinstance(entity, Coral):
        #     return False
        return True

    def position_subparts(self):
        for offset, part in self.parts.items():
            part.x = self.x + offset.x
            part.y = self.y + offset.y
            if isinstance(part, HumanLeftLeg) or isinstance(part, HumanRightLeg):
                # Move legs to animate swimming
                if time.time() % 0.5 < 0.25:
                    part.x += 1 if offset.x > 0 else -1
            # Animate arms
            if isinstance(part, HumanLeftArm) or isinstance(part, HumanRightArm):
                if time.time() % 0.5 < 0.25 and self.vertical_direction != 0:
                    part.y -= 1
            phase = 0.1 if self.vertical_direction == 1 else 0.4
            if isinstance(part, HumanLeftArm) and (self.direction == 1 or self.vertical_direction != 0):
                part.symbol = "🫷" if (time.time() + phase) % 0.5 < 0.25 else "👋" # 🖐️💪
            if isinstance(part, HumanRightArm) and (self.direction == -1 or self.vertical_direction != 0):
                part.symbol = "🫸" if (time.time() + phase) % 0.5 < 0.25 else "🫳" # 🫱
            # Point at object with attention
            if isinstance(part, HumanLeftArm) or isinstance(part, HumanRightArm):
                if self.attention is not None and self.vertical_direction == 0 and self.direction == 0:
                    part.symbol = "👈" if self.attention.x < part.x - 1 else "👉" if self.attention.x > part.x + 1 else "👇" if self.attention.y >= part.x else "👆"
                elif part.symbol in "👈👉👇👆":
                    part.symbol = "🖐️" # don't keep pointing after moving on

class GardenEel(BottomDweller):
    def __init__(self, x: int, y: int):
        super().__init__(x, y, 'S') # 🪱𓆙〰️〰𓆓〽𓆑

    def move(self):
        # If we're on the ground (and not just any solid entity),
        # "burrow" into it (by staying put and changing symbol)
        if entity_at(Offset(self.x, self.y + 1), Ground.instances):
            if random.random() < 0.1:
                self.symbol = random.choice('()⎛⎞/\\|,')
        else:
            self.symbol = 'S'
            super().move()


# Initialize the entities
def random_pos():
    return random.randint(0, tank_width), random.randint(0, tank_height)
for _ in range(5):
    Fish(*random_pos())
for _ in range(5):
    SeaUrchin(*random_pos())
for _ in range(2):
    BottomDweller(*random_pos())
for _ in range(2):
    Cephalopod(*random_pos())
for _ in range(5):
    Coral(*random_pos())
for _ in range(5):
    Shell(*random_pos())
for _ in range(5):
    Rock(*random_pos())
for _ in range(10):
    Seaweed(*random_pos())
for _ in range(2):
    Human(*random_pos())

def ground_height(x: int) -> int:
    return 4 + int(2 * math.sin(x / 10) + 1 * math.sin(x / 5) + 1 * math.sin(x / 2))

def generate_ground():
    for ground in list(Ground.instances):
        ground.remove_from_lists()
    for x in range(tank_width):
        for y in range(tank_height-ground_height(x), tank_height):
            Ground(x, y)

generate_ground()

garden_eel_colony_x = random.randint(0, tank_width)
for _ in range(5):
    eel_x = garden_eel_colony_x + random.randint(-8, 8)
    GardenEel(eel_x, tank_height - ground_height(eel_x) - 1)

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
        dragging: list[Entity] = []
        if self.dragging is not None:
            dragging = [self.dragging]
            if isinstance(self.dragging, HumanBodyPart):
                # dragging = [self.dragging.human, *self.dragging.human.parts.values()]
                dragging = [self.dragging.human]
        for entity in Entity.instances:
            if entity not in dragging:
                entity.move()
        # Update the screen
        self.refresh()

    def on_mount(self):
        self.set_interval(0.1, self.update)

    def render_line(self, y: int) -> Strip:
        """Render a line of the widget."""
        bg_color = light_blue.blend(dark_blue, y / self.size.height)
        bg_style = Style(bgcolor=bg_color.rich_color)
        entities_at_y = [entity for entity in Entity.instances if entity.y == y]
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
            # Alpha is supported for foreground colors, but not background colors currently,
            # used for Ink entities.
            ent_fg = entity.color.blend(bg_color, 1 - entity.color.a).rich_color
            ent_bg = entity.bgcolor.rich_color if entity.bgcolor is not None else None
            entity_style = bg_style + Style(color=ent_fg, bgcolor=ent_bg)
            entity_segment = Segment(entity.symbol, entity_style, None)
            segments.append(entity_segment)
            entity.symbol_width = entity_segment.cell_length
            x = new_x + entity_segment.cell_length

        segments.append(Segment(" " * (self.size.width - x), bg_style, None))
        return Strip(segments)

    def on_mouse_down(self, event: events.MouseDown) -> None:
        self.capture_mouse()
        self.dragging = entity_at(event.offset, Entity.instances)
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
            if isinstance(self.dragging, HumanBodyPart):
                self.dragging.human.x = self.dragging.x
                self.dragging.human.y = self.dragging.y
                self.dragging.human.position_subparts()
        elif random.random() < 0.5:
            Bubble(event.offset.x, event.offset.y)

class EmojiAquariumApp(App):
    def on_resize(self, event: events.Resize) -> None:
        global tank_width, tank_height

        # Move everything up/down to keep things anchored relative to the bottom of the tank.
        # Do this before re-generating the ground, so that the new ground doesn't get offset.
        for entity in Entity.instances:
            entity.y += event.size.height - tank_height

        tank_width = event.size.width
        tank_height = event.size.height

        generate_ground()

    def compose(self) -> ComposeResult:
        yield Tank()

app = EmojiAquariumApp()

# Must be before app.run() which blocks until the app exits.
# Takes the app in order to do some clean up of the app before restarting.
restart_on_changes(app)

if __name__ == "__main__":
    app.run()
