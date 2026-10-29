# =============================================================================
# SPACE INVADERS: STAR WARS EDITION
# A PyGame-based arcade game where the player controls an X-Wing fighter
# to destroy Tie Fighters and avoid Imperial Destroyers
# =============================================================================

import pygame
import random
import time


# =============================================================================
# INITIALIZATION SECTION
# Sets up Pygame, screen dimensions, and audio resources
# =============================================================================

# Initialize Pygame library
pygame.init()

# Screen dimensions configuration
screen_width = 800
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("The Imperials Destroy or Avoid I will")

# Load and configure sound effects
collision_sound = pygame.mixer.Sound("../Sounds/ship_explosion.mp3")
collision_sound.set_volume(0.5)  # Explosion sound volume at 50%

# Create a lower volume explosion sound for Tie Fighters (60% of X-Wing volume)
tie_fighter_explosion_sound = pygame.mixer.Sound("../Sounds/ship_explosion.mp3")
tie_fighter_explosion_sound.set_volume(0.5 * 0.6)  # 60% of 0.5 = 0.3

tie_sound = pygame.mixer.Sound("../Sounds/Tie_fighter.mp3")
tie_sound.set_volume(0.1)  # Tie fighter sound volume at 10%

game_music = pygame.mixer.Sound("../Sounds/imperial_march.mp3")
game_music.set_volume(0.5)  # Background music volume at 50%

# Set up the game clock for controlling frame rate
clock = pygame.time.Clock()

# Initialize start time for game progression tracking
start_time = time.time()


# =============================================================================
# HIGH SCORE MANAGEMENT
# Loads previous high score from file and provides functions to update it
# =============================================================================

# Initialize high score from file or set to 0 if file doesn't exist
high_score = 0
try:
    with open('../high_score.txt', 'r') as file:
        high_score = int(file.read())
except FileNotFoundError:
    # If high score file doesn't exist, start with 0
    pass


# =============================================================================
# ASSET LOADING SECTION
# Loads all image assets used in the game
# =============================================================================

# Load player and enemy sprites
x_wing_image = pygame.image.load("../images/x_wing.png").convert()
x_wing_image.set_colorkey((0, 0, 0))  # Make black background transparent
tie_fighter_image = pygame.image.load("../images/tie_fighter.png").convert()
tie_fighter_image.set_colorkey((5, 5, 5))  # Make dark grey background transparent

# Load Imperial Destroyer variants
imperial_destroyer_image = pygame.image.load("../images/imperial_destroyer.PNG").convert()
imperial_destroyer_image.set_colorkey((0, 0, 0))
imperial_destroyer_small_image = pygame.image.load("../images/imperial_destroyer_small.PNG").convert()
imperial_destroyer_small_image.set_colorkey((0, 0, 0))
imperial_destroyer_large_image = pygame.image.load("../images/imperial_destroyer_large.PNG").convert()
imperial_destroyer_large_image.set_colorkey((0, 0, 0))

# Load Darth Vader image for game over screen
darth_vader_image = pygame.image.load("../images/Darth_Vader.png").convert()
darth_vader_image.set_colorkey((0, 0, 0))  # Make white background transparent

# Load background image
background_image = pygame.image.load("../images/Background_DeathStar.png")

# Load explosion sprite sheet (12 frames, each 96x96 pixels)
explosion_sheet = pygame.image.load("../images/Explosion.png")


# =============================================================================
# EXPLOSION ANIMATION CLASS
# Handles the explosion animation with 12 frames
# =============================================================================

class Explosion:
    """
    Animation for X-Wing explosion with 12 frames
    Plays simultaneously with explosion sound
    """
    
    def __init__(self, x, y):
        """Initialize explosion at given position with 12 frames from sprite sheet"""
        # Each frame is 96x96 pixels (1152 total width / 12 frames = 96 per frame)
        self.frame_width = 96
        self.frame_height = 96
        self.total_frames = 12
        
        # Extract all frames from the sprite sheet
        self.frames = []
        for i in range(self.total_frames):
            frame_rect = pygame.Rect(
                i * self.frame_width, 
                0, 
                self.frame_width, 
                self.frame_height
            )
            frame = explosion_sheet.subsurface(frame_rect).copy()
            # Make black background transparent
            frame.set_colorkey((0, 0, 0))
            self.frames.append(frame)
        
        # Animation state
        self.current_frame = 0
        self.animation_speed = 2  # Frames per update (controls animation speed)
        self.frame_counter = 0
        self.x = x
        self.y = y
        self.completed = False
        
        # Position the explosion at the center of the X-Wing
        self.rect = self.frames[0].get_rect()
        self.rect.centerx = x
        self.rect.centery = y
    
    def update(self):
        """Update animation frame"""
        self.frame_counter += 1
        if self.frame_counter >= self.animation_speed:
            self.frame_counter = 0
            self.current_frame += 1
            if self.current_frame >= self.total_frames:
                self.current_frame = self.total_frames - 1
                self.completed = True
    
    def draw(self, surface):
        """Draw current animation frame on the given surface"""
        surface.blit(self.frames[self.current_frame], self.rect)


# =============================================================================
# GAME OBJECT CLASSES
# Defines all game entities and their behaviors
# =============================================================================

class XWing:
    """
    Player-controlled spaceship (X-Wing fighter)
    Handles movement, scoring, and bullet firing mechanics
    """
    
    def __init__(self):
        """Initialize X-Wing with image, position, speed, and movement controls"""
        # Set up sprite image and rectangle for collision detection
        self.image = x_wing_image
        self.rect = self.image.get_rect()
        
        # Position X-Wing at bottom center of screen
        self.rect.x = screen_width / 2 - self.rect.width / 2
        self.rect.y = screen_height - self.rect.height - 10
        
        # Movement configuration
        self.speed = 5
        self.move_left = False
        self.move_right = False
        self.move_up = False
        self.move_down = False
        self.can_move = True  # Flag to enable/disable movement
        
        # Game state tracking
        self.score = 0
        
        # Bullet management
        self.bullets = []
        self.bullet_image = pygame.Surface((10, 20))
        self.bullet_image.fill((255, 0, 0))
    
    def fire(self):
        """Create a new bullet at X-Wing's position and add to bullets list"""
        bullet = Bullet(self.rect.centerx, self.rect.top)
        self.bullets.append(bullet)

    def update(self):
        """
        Update X-Wing position based on movement flags
        Update all active bullets and handle bullet collisions
        """
        # Only move if allowed
        if self.can_move:
            # Handle horizontal movement
            if self.move_left:
                self.rect.x -= self.speed
            if self.move_right:
                self.rect.x += self.speed
            
            # Handle vertical movement
            if self.move_up:
                self.rect.y -= self.speed
            if self.move_down:
                self.rect.y += self.speed
            
            # Ensure X-Wing stays within screen boundaries
            # Left boundary: x >= 0
            if self.rect.x < 0:
                self.rect.x = 0
            # Right boundary: x + width <= screen_width
            if self.rect.x > screen_width - self.rect.width:
                self.rect.x = screen_width - self.rect.width
            # Top boundary: y >= 0
            if self.rect.y < 0:
                self.rect.y = 0
            # Bottom boundary: y + height <= screen_height
            if self.rect.y > screen_height - self.rect.height:
                self.rect.y = screen_height - self.rect.height
        
        # Update all active bullets
        bullets_to_remove = []
        for bullet in self.bullets:
            bullet.update()
            
            # Check if bullet has flown off the top of the screen
            if bullet.rect.y < -bullet.rect.height:
                bullets_to_remove.append(bullet)
                continue  # Skip collision checks for this bullet
            
            # Check for collision with each Tie Fighter
            for tie_fighter in tie_fighters[:]:
                if bullet.rect.colliderect(tie_fighter.rect):
                    self.score += 10  # Add points for hitting a Tie Fighter
                    tie_fighters.remove(tie_fighter)
                    
                    # Create explosion at Tie Fighter position
                    tie_fighter_explosions.append(Explosion(tie_fighter.rect.centerx, tie_fighter.rect.centery))
                    
                    # Play explosion sound at 60% of X-Wing volume
                    tie_fighter_explosion_sound.play()
                    
                    # Spawn a new Tie Fighter to replace the destroyed one
                    new_tie_fighter = TieFighter()
                    tie_fighters.append(new_tie_fighter)
                    
                    # Mark bullet for removal
                    bullets_to_remove.append(bullet)
                    break  # Only hit one Tie Fighter per bullet
        
        # Remove all marked bullets
        for bullet in bullets_to_remove:
            if bullet in self.bullets:
                self.bullets.remove(bullet)


class Bullet(pygame.sprite.Sprite):
    """
    Projectile fired by the X-Wing
    Moves upward and handles collision with enemies
    """
    
    def __init__(self, x, y):
        """Initialize bullet with position and appearance"""
        super().__init__()
        # Create bullet sprite (small blue rectangle)
        self.image = pygame.Surface((2, 30))
        self.image.fill((0, 0, 255))  # Blue color
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.bottom = y
        self.speed = -10  # Negative for upward movement
    
    def update(self):
        """
        Move bullet upward and check for collisions or screen boundaries
        """
        self.rect.y += self.speed
        
        # Remove bullet if it goes off the top of the screen
        if self.rect.bottom < 0:
            self.kill()
        
        # Check collision with Tie Fighters
        for tie_fighter in tie_fighters[:]:
            if self.rect.colliderect(tie_fighter.rect):
                self.kill()
    
    def kill(self):
        """Remove bullet from active sprites"""
        super().kill()  # Call the Sprite class's kill method to remove it


class TieFighter:
    """
    Enemy spaceship that moves downward with increasing speed over time
    Spawns new enemies as the game progresses
    """
    
    def __init__(self):
        """Initialize Tie Fighter with random position and speed"""
        # Set up sprite image and rectangle
        self.image = tie_fighter_image
        self.rect = self.image.get_rect()
        
        # Random starting position above the screen
        self.rect.x = random.randint(0, screen_width - self.rect.width)
        self.rect.y = random.randint(-500, -50)
        
        # Movement configuration with random variation
        self.initial_speed = random.randint(1, 4)
        self.speed = self.initial_speed
        self.initial_x_speed = random.randint(-2, 2)  # Horizontal movement
        self.x_speed = self.initial_x_speed
        
        # Spawning configuration
        self.initial_spawn_rate = 5  # Spawn a new Tie Fighter every 5 seconds initially
        self.spawn_rate = self.initial_spawn_rate
        
        # Timing and state tracking
        self.time = time.time()
        self.passed = False  # Flag for when Tie Fighter passes bottom of screen
    
    def check_collision(self, bullets):
        """Check if any bullet collides with this Tie Fighter"""
        for bullet in bullets:
            if self.rect.colliderect(bullet):
                return True
        return False

    def update(self):
        """
        Update Tie Fighter position and spawn new enemies based on game progression
        Returns 1 point if Tie Fighter passes the bottom of the screen
        """
        # Increase speed and spawn rate over time (difficulty scaling)
        current_time = time.time()
        if current_time - self.time >= self.spawn_rate:
            self.time = current_time
            # Increase speed by 10% every 30 seconds
            self.speed = self.initial_speed * (1 + (current_time - start_time) / 30)
            self.x_speed = self.initial_x_speed
            # Spawn a new Tie Fighter
            tie_fighters.append(TieFighter())
            # Decrease spawn rate (spawn more frequently) over time
            self.spawn_rate = self.initial_spawn_rate / (1 + (current_time - start_time) / 60)

        # Update position based on speed
        self.rect.y += self.speed
        self.rect.x += self.x_speed
        
        # Check if Tie Fighter has passed the bottom of the screen
        if self.rect.y > screen_height:
            self.passed = True
            return 1  # Return 1 point earned (player loses points when enemies pass)
        else:
            return 0  # Return 0 points earned
        
    def play_tie_sound(self):
        """Play Tie Fighter sound effect when appropriate"""
        global tie_sound_played
        tie_sound_played = False
        if not self.passed and not tie_sound_played:
            tie_sound.play()
            tie_sound_played = True
        elif self.passed:
            tie_sound_played = False


class ImperialDestroyer:
    """
    Enemy spaceship that moves downward slowly
    Randomly chooses between small, normal, or large variants
    Acts as a secondary obstacle for the player
    """
    
    def __init__(self):
        """Initialize Imperial Destroyer with random position and random size variant"""
        # Randomly choose between small, normal, or large variant
        variant = random.choice(['small', 'normal', 'large'])
        
        # Set up sprite image based on chosen variant
        if variant == 'small':
            self.image = imperial_destroyer_small_image
        elif variant == 'large':
            self.image = imperial_destroyer_large_image
        else:
            self.image = imperial_destroyer_image
        
        self.rect = self.image.get_rect()
        
        # Random starting position above the screen
        self.rect.x = random.randint(0, screen_width - self.rect.width)
        self.rect.y = random.randint(-1000, -500)
        
        # Movement configuration (slow downward movement)
        self.speed = 1

    def update(self):
        """Move Imperial Destroyer downward"""
        self.rect.y += self.speed


# =============================================================================
# MAIN GAME LOOP
# Controls the game flow, event handling, updates, and rendering
# =============================================================================

# Main game running flag
running = True

while running:
    # -------------------------------------------------------------------------
    # GAME SETUP SECTION
    # Initialize game objects and state for a new game
    # -------------------------------------------------------------------------
    
    # Create player X-Wing
    x_wing = XWing()
    
    # Initialize enemy lists
    tie_fighters = []
    imperial_destroyers = []
    
    # Initialize explosions list for Tie Fighters
    tie_fighter_explosions = []
    
    # Initialize explosion (None at start) for X-Wing
    x_wing_explosion = None
    x_wing_explosion_active = False
    
    # Sound state tracking
    tie_sound_played = False
    last_tie_fighter_time = 0  # Track time when last tie fighter was added
    tie_fighter_interval = 5000  # Add a new tie fighter every 5 seconds

    # Create initial Tie Fighters (10 enemies)
    for i in range(10):
        tie_fighter = TieFighter()
        tie_fighters.append(tie_fighter)

    # Create initial Imperial Destroyers (3 large enemies)
    for i in range(3):
        imperial_destroyer = ImperialDestroyer()
        imperial_destroyers.append(imperial_destroyer)

    # Game state flags
    game_over = False
    game_music.play(loops=-1,)  # Start background music looping
    initial = True  # Flag for initial start screen
    
    # -------------------------------------------------------------------------
    # GAME PLAY LOOP
    # Runs until player loses (game_over = True)
    # -------------------------------------------------------------------------
    
    while not game_over:
        
        # =====================================================================
        # START SCREEN HANDLING
        # Displays instructions and waits for player to start
        # =====================================================================
        
        if initial == True:
            # Draw background
            screen.blit(background_image, (0, 0))
            
            # Draw game title
            font = pygame.font.SysFont("Arial", 40)
            message1 = font.render("Destroy Tie Fighters or Die", True, (0, 0, 255))
            screen.blit(message1, (screen_width/2 - message1.get_width()/2, screen_height/2 - 200))
            
            # Draw game instructions
            font = pygame.font.SysFont("Arial", 20)
            message2 = font.render("Use ´Arrow keys´ to move the X-Wing", True, (255, 255, 255))
            screen.blit(message2, (screen_width/2 - message2.get_width()/2, screen_height/2 + 100))
            
            message3 = font.render("Use ´Left Control´ or 'Space' to fire", True, (255, 255, 255))
            screen.blit(message3, (screen_width/2 - message3.get_width()/2, screen_height/2 + 150))
            
            message4 = font.render("Press ´Esc´ to end the game", True, (255, 255, 255))
            screen.blit(message4, (screen_width/2 - message4.get_width()/2, screen_height/2 + 200))
            
            message5 = font.render("Press any key to start", True, (255, 255, 255))
            screen.blit(message5, (screen_width/2 - message5.get_width()/2, screen_height/2 + 250))
            
            pygame.display.update()
            
            # Wait for any key press to start the game
            waiting_for_start = True
            while waiting_for_start:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        game_over = True
                        waiting_for_start = False
                    elif event.type == pygame.KEYDOWN:
                        waiting_for_start = False
                        initial = False
            continue  # Skip the rest of the frame
        
        # =====================================================================
        # EVENT HANDLING SECTION
        # Processes keyboard and window events
        # =====================================================================
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_over = True
            
            elif event.type == pygame.KEYDOWN:
                # Handle key press events for movement and actions
                if event.key == pygame.K_ESCAPE:
                    game_over = True
                elif event.key == pygame.K_LEFT:
                    x_wing.move_left = True
                elif event.key == pygame.K_RIGHT:
                    x_wing.move_right = True
                elif event.key == pygame.K_UP:
                    x_wing.move_up = True
                elif event.key == pygame.K_DOWN:
                    x_wing.move_down = True
                elif event.key == pygame.K_LCTRL:
                    x_wing.fire()
                elif event.key == pygame.K_SPACE:
                    x_wing.fire()
            
            elif event.type == pygame.KEYUP:
                # Handle key release events to stop movement
                if event.key == pygame.K_LEFT:
                    x_wing.move_left = False
                elif event.key == pygame.K_RIGHT:
                    x_wing.move_right = False
                elif event.key == pygame.K_UP:
                    x_wing.move_up = False
                elif event.key == pygame.K_DOWN:
                    x_wing.move_down = False
        
        # =====================================================================
        # GAME LOGIC UPDATES SECTION
        # Updates all game objects and handles collisions
        # =====================================================================
        
        # Update all Tie Fighter explosions
        for explosion in tie_fighter_explosions[:]:
            explosion.update()
            # Remove completed explosions
            if explosion.completed:
                tie_fighter_explosions.remove(explosion)
        
        # Check if X-Wing explosion is active and update it
        if x_wing_explosion_active and x_wing_explosion:
            x_wing_explosion.update()
            # If X-Wing explosion animation is complete, set game_over flag
            if x_wing_explosion.completed:
                game_over = True
                x_wing_explosion_active = False
        
        # Only update game objects if no X-Wing explosion is active
        if not x_wing_explosion_active:
            # Update all Tie Fighters
            for tie_fighter in tie_fighters[:]:
                # Update Tie Fighter position and spawn new ones
                x_wing.score += tie_fighter.update()
                
                # Handle Tie Fighters that have passed the bottom of the screen
                if tie_fighter.passed:
                    tie_fighters.remove(tie_fighter)
                    new_tie_fighter = TieFighter()
                    tie_fighters.append(new_tie_fighter)
                    tie_sound.play()
                    tie_fighter.play_tie_sound()

                # Check for collision between X-Wing and Tie Fighter
                if x_wing.rect.colliderect(tie_fighter.rect):
                    # Create explosion at X-Wing position
                    x_wing_explosion = Explosion(x_wing.rect.centerx, x_wing.rect.centery)
                    x_wing_explosion_active = True
                    x_wing.can_move = False  # Stop X-Wing movement
                    collision_sound.play()  # Play explosion sound
                    # Don't set game_over here - wait for explosion to finish
                    break  # Exit loop to prevent multiple explosions
            
            # Update all Imperial Destroyers
            for imperial_destroyer in imperial_destroyers[:]:
                imperial_destroyer.update()

                # Handle Imperial Destroyers that have passed the bottom of the screen
                if imperial_destroyer.rect.y > screen_height:
                    imperial_destroyers.remove(imperial_destroyer)
                    new_imperial_destroyer = ImperialDestroyer()
                    imperial_destroyers.append(new_imperial_destroyer)

                # Check for collision between X-Wing and Imperial Destroyer
                if x_wing.rect.colliderect(imperial_destroyer.rect):
                    # Create explosion at X-Wing position
                    x_wing_explosion = Explosion(x_wing.rect.centerx, x_wing.rect.centery)
                    x_wing_explosion_active = True
                    x_wing.can_move = False  # Stop X-Wing movement
                    collision_sound.play()  # Play explosion sound
                    # Don't set game_over here - wait for explosion to finish
                    break  # Exit loop to prevent multiple explosions
            
            # Update X-Wing position and bullets
            x_wing.update()
        
        # =====================================================================
        # RENDERING SECTION
        # Draws all game objects to the screen
        # =====================================================================
        
        # Draw background
        screen.blit(background_image, (0, 0))

        # Draw all Tie Fighters
        for tie_fighter in tie_fighters:
            screen.blit(tie_fighter.image, tie_fighter.rect)
        
        # Draw all active bullets
        for bullet in x_wing.bullets:
            screen.blit(bullet.image, bullet.rect)
        
        # Draw all Imperial Destroyers
        for imperial_destroyer in imperial_destroyers:
            screen.blit(imperial_destroyer.image, imperial_destroyer.rect)

        # Draw X-Wing (player ship)
        screen.blit(x_wing.image, x_wing.rect)
        
        # Draw all Tie Fighter explosions
        for explosion in tie_fighter_explosions:
            explosion.draw(screen)
        
        # Draw X-Wing explosion if active
        if x_wing_explosion_active and x_wing_explosion:
            x_wing_explosion.draw(screen)
        
        # Draw current score in the top-left corner
        font = pygame.font.SysFont("Arial", 24)
        score_text = font.render("Score: " + str(x_wing.score), True, (255, 255, 255))
        score_rect = score_text.get_rect()
        score_rect.topleft = (10, 10)
        screen.blit(score_text, score_rect)

        # Draw high score below current score
        high_score_text = font.render(f"High Score: {high_score}", True, (255, 255, 0))  # Yellow color
        high_score_rect = high_score_text.get_rect()
        high_score_rect.topleft = (10, 40)  # Placed slightly below the current score
        screen.blit(high_score_text, high_score_rect)

        # Update the display
        pygame.display.update()
        
        # Control game speed (60 FPS)
        clock.tick(60)

    # =========================================================================
    # GAME OVER SECTION
    # Handles game over screen, score display, and restart/exit options
    # =========================================================================
    
    # Display game over screen
    screen.fill((0, 0, 0))
    
    # Display Darth Vader image above text (centered at top of screen)
    vader_rect = darth_vader_image.get_rect()
    vader_rect.center = (screen_width / 2, screen_height / 3)
    screen.blit(darth_vader_image, vader_rect)
    
    # Display Game Over text below Darth Vader
    font = pygame.font.SysFont("Arial", 60)
    game_over_text = font.render("Game Over", True, (255, 0, 0))
    game_over_rect = game_over_text.get_rect()
    game_over_rect.center = (screen_width / 2, screen_height / 2 + 100)
    screen.blit(game_over_text, game_over_rect)
    
    # Fade out sounds
    game_music.fadeout(3000)
    tie_sound.fadeout(1000)
    pygame.display.update()
    
    # Update high score if current score is higher
    if x_wing.score > high_score:
        high_score = x_wing.score
    
    # Save high score to file
    with open('../high_score.txt', 'w') as file:
        file.write(str(high_score))
    
    # Display high score on game over screen (moved down)
    font = pygame.font.SysFont("Arial", 20)
    high_score_text = font.render(f"High Score: {high_score}", True, (255, 255, 0))
    high_score_rect = high_score_text.get_rect()
    high_score_rect.center = (screen_width / 2, screen_height / 2 + 160)
    screen.blit(high_score_text, high_score_rect)
    pygame.display.update()
    
    # Display player's score on game over screen (moved down)
    font = pygame.font.SysFont("Arial", 20)
    score_text = font.render(f"Your Score: {x_wing.score}", True, (255, 255, 255))
    score_rect = score_text.get_rect()
    score_rect.center = (screen_width / 2, screen_height / 2 + 190)
    screen.blit(score_text, score_rect)
    pygame.display.update()
    
    # Display restart/exit instructions
    font = pygame.font.Font(None, 25)
    message = font.render("Press any key to restart or Esc to exit", True, (255, 255, 255))
    screen.blit(message, (screen_width/2 - message.get_width()/2, screen_height - 50))
    pygame.display.update()
    
    # Wait for 1 second before allowing restart (after game over screen is seen)
    wait_start_time = time.time()
    waiting_for_restart = True
    restart_allowed = False
    
    while waiting_for_restart:
        # Check if 1 second has passed
        if time.time() - wait_start_time >= 1.0:
            restart_allowed = True
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                waiting_for_restart = False
            elif event.type == pygame.KEYDOWN:
                if restart_allowed:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                        waiting_for_restart = False
                    else:
                        # Reset game state for a new game
                        game_over = False
                        initial = True
                        start_time = time.time()
                        
                        waiting_for_restart = False
    
    # Clean up and exit if player chose to quit
    if not running:
        pygame.mixer.quit()
        pygame.quit()
