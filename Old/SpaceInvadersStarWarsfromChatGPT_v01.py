import pygame
import random

# Initialize pygame
pygame.init()

# Set up the screen
screen_width = 800
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("X-Wing Invaders")

# Set up the game clock
clock = pygame.time.Clock()

# Load the images
x_wing_image = pygame.image.load("x_wing.png")
tie_fighter_image = pygame.image.load("tie_fighter.png")

# Define the game objects
class XWing:
    def __init__(self):
        self.image = x_wing_image
        self.rect = self.image.get_rect()
        self.rect.x = screen_width / 2 - self.rect.width / 2
        self.rect.y = screen_height - self.rect.height - 10
        self.speed = 5
        self.move_left = False
        self.move_right = False

    def update(self):
        if self.move_left:
            self.rect.x -= self.speed
        if self.move_right:
            self.rect.x += self.speed

class TieFighter:
    def __init__(self):
        self.image = tie_fighter_image
        self.rect = self.image.get_rect()
        self.rect.x = random.randint(0, screen_width - self.rect.width)
        self.rect.y = random.randint(-500, -50)
        self.speed = random.randint(1, 4)

    def update(self):
        self.rect.y += self.speed

# Set up the game
x_wing = XWing()
tie_fighters = []

for i in range(10):
    tie_fighter = TieFighter()
    tie_fighters.append(tie_fighter)

# Main game loop
game_over = False

while not game_over:
    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            game_over = True
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                x_wing.move_left = True
            elif event.key == pygame.K_RIGHT:
                x_wing.move_right = True
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_LEFT:
                x_wing.move_left = False
            elif event.key == pygame.K_RIGHT:
                x_wing.move_right = False

    # Update game objects
    for tie_fighter in tie_fighters:
        tie_fighter.update()

        if tie_fighter.rect.y > screen_height:
            tie_fighters.remove(tie_fighter)
            new_tie_fighter = TieFighter()
            tie_fighters.append(new_tie_fighter)

    # Check for collisions
    for tie_fighter in tie_fighters:
        if x_wing.rect.colliderect(tie_fighter.rect):
            game_over = True

    # Update the player
    x_wing.update()

    # Draw the screen
    screen.fill((0, 0, 0))
    screen.blit(x_wing.image, x_wing.rect)

    for tie_fighter in tie_fighters:
        screen.blit(tie_fighter.image, tie_fighter.rect)

    pygame.display.flip()

    # Wait for a short time
    clock.tick(60)

# Quit pygame
pygame.quit()
