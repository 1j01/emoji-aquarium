#!/usr/bin/env python3
import random
import time

# Escape sequence helpers
def set_background_color(row, color):
    """Draw a row of the background color gradient"""
    print(f"\033[{row+1};1H\033[48;2;{color[0]};{color[1]};{color[2]}m\033[K", end='')

def reset_color():
    """Reset the color to default"""
    print("\033[0m")

# Class hierarchy for entities
class Entity:
    def __init__(self, x, y, symbol):
        self.x = x
        self.y = y
        self.symbol = symbol

    def move(self):
        pass

    def draw(self):
        print(f"\033[{self.y+1};{self.x+1}H{self.symbol}")

class Fish(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, '🐠')
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
        super().__init__(x, y, '🦔')

    def move(self):
        self.y += 1

        # Wrap around the screen
        if self.y > 23:
            self.y = 0

class Seaweed(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, '🌿')

    def move(self):
        pass

class Bubble(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, '💦')

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
light_blue = (135, 206, 250)
dark_blue = (25, 25, 112)

# Clear the screen
print("\033[2J")

# Main loop
while True:
    # Set the background color for each row with a gradient
    for row in range(24):
        color = [
            int(light_blue[c] + (dark_blue[c] - light_blue[c]) * (row / 24))
            for c in range(3)
        ]
        set_background_color(row, color)

    # Move and draw entities
    for entity in fish + sea_urchins + seaweed + bubbles:
        entity.move()
        entity.draw()

    # Reset the color to default
    reset_color()

    # Sleep for a short while to control the speed
    time.sleep(0.1)
