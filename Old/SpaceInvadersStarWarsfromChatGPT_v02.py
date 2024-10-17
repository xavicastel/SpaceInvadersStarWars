import pygame
import random
import math

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
imperial_destroyer_image = pygame.image.load("imperial_destroyer.png")

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
        self.speed = random.randint(2, 4)

    def update(self):
        self.rect.y += self.speed

class ImperialDestroyer:
    def __init__(self):
        self.image = imperial_destroyer_image
        self.rect = self.image.get_rect()
        self.rect.x = random.randint(0, screen_width - self.rect.width)
        self.rect.y = random.randint(-1000, -500)
        self.speed = 1

    def update(self):
        self.rect.y += self.speed

# Set up the game
x_wing = XWing()
tie_fighters = []
imperial_destroyers = []

for i in range(10):
    tie_fighter = TieFighter()
    tie_fighters.append(tie_fighter)

for i in range(3):
    imperial_destroyer = ImperialDestroyer()
    imperial_destroyers.append(imperial_destroyer)

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

        if x_wing.rect.colliderect(tie_fighter.rect):
            game_over = True

    for imperial_destroyer in imperial_destroyers:
        imperial_destroyer.update()

        if imperial_destroyer.rect.y > screen_height:
            imperial_destroyers.remove(imperial_destroyer)
            new_imperial_destroyer = ImperialDestroyer()
            imperial_destroyers.append(new_imperial_destroyer)

        if x_wing.rect.colliderect(imperial_destroyer.rect):
            game_over = True

    x_wing.update()

    # Draw game objects
    screen.fill((0, 0, 0))

    for tie_fighter in tie_fighters:
        screen.blit(tie_fighter.image, tie_fighter.rect)

    for imperial_destroyer in imperial_destroyers:
        screen.blit(imperial_destroyer.image, imperial_destroyer.rect)

    screen.blit(x_wing.image, x_wing.rect)

    # Update the screen
    pygame.display.update()
    
    # Set the game FPS
    clock.tick(60)

# Set up the game over screen
if game_over:
    screen.fill((0, 0, 0))
    font = pygame.font.SysFont("Arial", 60)
    game_over_text = font.render("Game Over", True, (255, 255, 255))
    game_over_rect = game_over_text.get_rect()
    game_over_rect.center = (screen_width / 2, screen_height / 2)
    screen.blit(game_over_text, game_over_rect)
    pygame.display.update()
    pygame.time.delay(1500)
    pygame.quit()

