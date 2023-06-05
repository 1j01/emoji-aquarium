#!/usr/bin/env python3
import random
import time

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

# Clear the screen
print("\033[2J")

# Main loop
while True:
    # Move and draw entities
    for entity in fish + sea_urchins + seaweed + bubbles:
        entity.move()
        entity.draw()

    # Sleep for a short while to control the speed
    time.sleep(0.1)
