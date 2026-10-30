# =============================================================================
# SPACE INVADERS: STAR WARS EDITION
# A PyGame-based arcade game where the player controls an X-Wing fighter
# to destroy Tie Fighters and avoid Imperial Destroyers
#
# ASYNC + TOUCH VERSION
#   - Runs in PyCharm (desktop), desktop browser and mobile browser (Pygbag)
#   - Keyboard: Arrow keys to move, Space / Left Ctrl to fire, Esc to end
#   - Touch / mouse drag: drag anywhere to move the X-Wing (relative to where
#     you touched, so your finger never covers the ship), the X-Wing fires
#     automatically while a finger is down. Tap to start / restart.
#
# MOBILE AUDIO / PERFORMANCE FIXES IN THIS VERSION
#   1. Larger audio buffer on the web (pre_init) -> avoids crackling underruns
#   2. Waiting loops (start screen, game over) now call clock.tick() so they
#      no longer spin at 100% CPU and starve the audio thread
#   3. Explosion frames are cut from the sprite sheet ONCE at start-up
#      instead of on every explosion (was a big per-explosion CPU spike)
#   4. Tie Fighter sound is rate-limited (it was triggered twice per enemy
#      and could stack many overlapping voices)
#   5. Images are converted to the display format (faster blitting)
#   6. Limited number of mixer channels
# =============================================================================

import asyncio
import pygame
import random
import time
import sys


# =============================================================================
# PLATFORM DETECTION
# =============================================================================

IS_WEB = sys.platform == "emscripten"


# =============================================================================
# INITIALIZATION SECTION
# Sets up Pygame, screen dimensions, and audio resources
# =============================================================================

# The mixer must be configured BEFORE pygame.init().
# Mobile browsers have a slow audio path: a small buffer underruns and causes
# crackling / distortion, so use a big buffer on the web.
#   args: frequency, size (16-bit signed), channels (stereo), buffer
pygame.mixer.pre_init(44100, -16, 2, 4096 if IS_WEB else 1024)

# Initialize Pygame library
pygame.init()

# Fewer simultaneous voices = less mixing work for phones
pygame.mixer.set_num_channels(8)

# Screen dimensions configuration
screen_width = 800
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))
screen_rect = screen.get_rect()
pygame.display.set_caption("The Imperials Destroy or Avoid I will")

# Load and configure sound effects
collision_sound = pygame.mixer.Sound("Sounds/ship_explosion.ogg")
collision_sound.set_volume(0.5)  # Explosion sound volume at 50%

# Create a lower volume explosion sound for Tie Fighters (60% of X-Wing volume)
tie_fighter_explosion_sound = pygame.mixer.Sound("Sounds/ship_explosion.ogg")
tie_fighter_explosion_sound.set_volume(0.5 * 0.6)  # 60% of 0.5 = 0.3

tie_sound = pygame.mixer.Sound("Sounds/tie_fighter.ogg")
tie_sound.set_volume(0.1)  # Tie fighter sound volume at 10%

pygame.mixer.music.load("Sounds/imperial_march.ogg")
pygame.mixer.music.set_volume(0.5)  # Background music volume at 50%

# Set up the game clock for controlling frame rate
clock = pygame.time.Clock()

# Initialize start time for game progression tracking
start_time = time.time()

# Rate limiter for the Tie Fighter flyby sound (seconds between plays)
TIE_SOUND_MIN_INTERVAL = 0.25
_last_tie_sound_time = 0.0


def play_tie_sound():
    """Play the Tie Fighter sound, but never more often than the interval."""
    global _last_tie_sound_time
    now = time.time()
    if now - _last_tie_sound_time >= TIE_SOUND_MIN_INTERVAL:
        tie_sound.play()
        _last_tie_sound_time = now


# =============================================================================
# HIGH SCORE MANAGEMENT
# Loads previous high score from file and provides functions to update it
# =============================================================================

def load_high_score():
    """Read the high score from localStorage (web) or high_score.txt (desktop)."""
    try:
        if IS_WEB:
            import platform
            value = platform.window.localStorage.getItem("high_score")
            return int(value) if value else 0
        else:
            with open("high_score.txt", "r") as f:
                return int(f.read())
    except Exception:
        # Missing file, empty value, corrupted content, storage blocked...
        return 0

def save_high_score(score):
    """Write the high score to localStorage (web) or high_score.txt (desktop)."""
    try:
        if IS_WEB:
            import platform
            platform.window.localStorage.setItem("high_score", str(score))
        else:
            with open("high_score.txt", "w") as f:
                f.write(str(score))
    except Exception:
        pass  # Never let a saving problem crash the game

# Initialize high score from file or set to 0 if file doesn't exist
high_score = load_high_score()

# =============================================================================
# ASSET LOADING SECTION
# Loads all image assets used in the game
# =============================================================================

# Load player and enemy sprites
x_wing_image = pygame.image.load("images/x_wing.png").convert()
x_wing_image.set_colorkey((0, 0, 0))  # Make black background transparent
tie_fighter_image = pygame.image.load("images/tie_fighter.png").convert()
tie_fighter_image.set_colorkey((5, 5, 5))  # Make dark grey background transparent

# Load Imperial Destroyer variants
imperial_destroyer_image = pygame.image.load("images/imperial_destroyer.png").convert()
imperial_destroyer_image.set_colorkey((0, 0, 0))
imperial_destroyer_small_image = pygame.image.load("images/imperial_destroyer_small.png").convert()
imperial_destroyer_small_image.set_colorkey((0, 0, 0))
imperial_destroyer_large_image = pygame.image.load("images/imperial_destroyer_large.png").convert()
imperial_destroyer_large_image.set_colorkey((0, 0, 0))

# Load Darth Vader image for game over screen
darth_vader_image = pygame.image.load("images/darth_vader.png").convert()
darth_vader_image.set_colorkey((0, 0, 0))  # Make black background transparent

# Load X-Wing welcome image for start screen
x_wing_welcome_image = pygame.image.load("images/x-wing-welcome.png").convert()
x_wing_welcome_image.set_colorkey((0, 0, 0))

# Load background image (convert() = faster blit every frame)
background_image = pygame.image.load("images/background_deathstar.png").convert()

# Load explosion sprite sheet (12 frames, each 96x96 pixels)
explosion_sheet = pygame.image.load("images/explosion.png").convert()

# =============================================================================
# EXPLOSION FRAMES (CUT ONCE)
# Previously every Explosion object re-cut and copied 12 frames. On a phone
# that caused a visible hiccup (and audio glitches) each time something blew up.
# =============================================================================

EXPLOSION_FRAME_SIZE = 96
EXPLOSION_TOTAL_FRAMES = 12
EXPLOSION_FRAMES = []
for _i in range(EXPLOSION_TOTAL_FRAMES):
    _rect = pygame.Rect(_i * EXPLOSION_FRAME_SIZE, 0, EXPLOSION_FRAME_SIZE, EXPLOSION_FRAME_SIZE)
    _frame = explosion_sheet.subsurface(_rect).copy()
    _frame.set_colorkey((0, 0, 0))  # Make black background transparent
    EXPLOSION_FRAMES.append(_frame)

# =============================================================================
# FONT DECLARATIONS
# Reusable font objects to avoid recreating them in the game loop
# =============================================================================

font_20 = pygame.font.Font("fonts/freesansbold.ttf", 20)
font_25 = pygame.font.Font("fonts/freesansbold.ttf", 25)
font_40 = pygame.font.Font("fonts/freesansbold.ttf", 40)
font_60 = pygame.font.Font("fonts/freesansbold.ttf", 60)


# =============================================================================
# POINTER INPUT (TOUCH + MOUSE)
# One small class that turns touch-screen and mouse events into three simple
# actions: 'down', 'move' (with dx, dy) and 'up'.
#
# Designed to be tolerant of how different browsers report touches:
#   - Finger ids are NOT used. Any finger-up (or mouse-up) releases the
#     pointer, so a lost/mismatched id can never leave the ship "stuck".
#   - A new finger-down always re-syncs the state (self-healing).
#   - Browsers often send emulated MOUSE events for the same touch. Mouse
#     MOVEMENT is ignored for a moment after a finger event so the ship does
#     not move twice, but mouse UP always releases (extra safety net).
#   - Single-touch play: the last finger to touch is the one that steers.
# =============================================================================

TOUCH_SENSITIVITY = 1.2      # >1 = ship moves slightly more than the finger
FINGER_PRIORITY_SECONDS = 0.5  # ignore emulated mouse motion this long after a finger event
DEBUG_TOUCH = False          # True = show touch state on screen (for troubleshooting)


class PointerInput:
    def __init__(self):
        self.down = False             # Is a finger / mouse button currently down?
        self.finger_last = None       # last finger position (pixels)
        self.mouse_last = None        # last mouse position (pixels)
        self.last_finger_time = -10.0  # time of the last finger event
        self.last_event_name = "-"    # for DEBUG_TOUCH

    def reset(self):
        """Forget any held finger (call when a new game starts)."""
        self.down = False
        self.finger_last = None
        self.mouse_last = None

    def _finger_recent(self):
        return time.time() - self.last_finger_time < FINGER_PRIORITY_SECONDS

    def handle(self, event):
        """
        Feed one pygame event. Returns None, or a tuple (kind, dx, dy)
        where kind is 'down', 'move' or 'up'.
        """
        t = event.type

        # ---------------- Touch screen ----------------
        if t == pygame.FINGERDOWN:
            self.last_finger_time = time.time()
            self.last_event_name = "FINGERDOWN"
            self.down = True
            self.finger_last = (event.x * screen_width, event.y * screen_height)
            return ('down', 0, 0)

        if t == pygame.FINGERMOTION:
            self.last_finger_time = time.time()
            self.last_event_name = "FINGERMOTION"
            pos = (event.x * screen_width, event.y * screen_height)
            if not self.down or self.finger_last is None:
                self.finger_last = pos
                return None
            dx, dy = pos[0] - self.finger_last[0], pos[1] - self.finger_last[1]
            self.finger_last = pos
            return ('move', dx, dy)

        if t == pygame.FINGERUP:
            self.last_finger_time = time.time()
            self.last_event_name = "FINGERUP"
            was_down = self.down
            self.down = False
            self.finger_last = None
            return ('up', 0, 0) if was_down else None

        # ---------------- Mouse (desktop, or emulated touch) ----------------
        if t == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.last_event_name = "MOUSEDOWN"
            self.mouse_last = event.pos
            if self.down:
                return None  # already down (finger event came first)
            self.down = True
            return ('down', 0, 0)

        if t == pygame.MOUSEMOTION:
            if not self.down or self._finger_recent():
                self.mouse_last = event.pos
                return None
            if self.mouse_last is None:
                self.mouse_last = event.pos
                return None
            self.last_event_name = "MOUSEMOTION"
            dx, dy = event.pos[0] - self.mouse_last[0], event.pos[1] - self.mouse_last[1]
            self.mouse_last = event.pos
            return ('move', dx, dy)

        if t == pygame.MOUSEBUTTONUP and event.button == 1:
            self.last_event_name = "MOUSEUP"
            self.mouse_last = None
            was_down = self.down
            self.down = False
            self.finger_last = None
            return ('up', 0, 0) if was_down else None

        return None


pointer = PointerInput()


# =============================================================================
# EXPLOSION ANIMATION CLASS
# Handles the explosion animation with 12 frames
# =============================================================================

class Explosion:
    """
    Animation for explosions with 12 frames
    Plays simultaneously with explosion sound
    """

    def __init__(self, x, y):
        """Initialize explosion at given position (frames are shared, pre-cut)"""
        self.frames = EXPLOSION_FRAMES
        self.total_frames = EXPLOSION_TOTAL_FRAMES

        # Animation state
        self.current_frame = 0
        self.animation_speed = 2  # Frames per update (controls animation speed)
        self.frame_counter = 0
        self.x = x
        self.y = y
        self.completed = False

        # Position the explosion at the given center
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

        # Firing state
        self.firing = False        # keyboard fire button held
        self.touch_firing = False  # finger down (auto-fire on touch)

        # Game state tracking
        self.score = 0

        # Bullet management
        self.bullets = []
        self.bullet_image = pygame.Surface((10, 20))
        self.bullet_image.fill((255, 0, 0))
        self.next_bullet_side = 'left'  # Alternate between left and right edges

        # Firing rate control (in seconds)
        self.last_fire_time = 0
        self.initial_fire_interval = 0.3
        self.fire_interval = self.initial_fire_interval

    def drag(self, dx, dy):
        """Move the X-Wing by a finger/mouse drag (relative movement)"""
        if not self.can_move:
            return
        self.rect.x += int(dx * TOUCH_SENSITIVITY)
        self.rect.y += int(dy * TOUCH_SENSITIVITY)
        self.rect.clamp_ip(screen_rect)

    def fire(self):
        """Create a new bullet at X-Wing's left or right edge, alternating sides"""
        # Check if enough time has passed since last shot
        current_time = time.time()
        time_since_last_fire = current_time - self.last_fire_time

        # Decrease fire interval over time (fire faster as game progresses)
        game_time = current_time - start_time
        self.fire_interval = max(0.01, self.initial_fire_interval / (1 + game_time / 30))

        if time_since_last_fire >= self.fire_interval:
            # Determine which edge to fire from
            if self.next_bullet_side == 'left':
                x_pos = self.rect.left
            else:
                x_pos = self.rect.right

            bullet = Bullet(x_pos, self.rect.top)
            self.bullets.append(bullet)

            # Toggle for next bullet
            self.next_bullet_side = 'right' if self.next_bullet_side == 'left' else 'left'
            self.last_fire_time = current_time

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
            self.rect.clamp_ip(screen_rect)

        # Automatic firing when keyboard fire button OR a finger is held
        if self.firing or self.touch_firing:
            self.fire()

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
            self.spawn_rate = self.initial_spawn_rate / (0.5 + (current_time - start_time) / 60)

        # Update position based on speed
        self.rect.y += self.speed
        self.rect.x += self.x_speed

        # Check if Tie Fighter has passed the bottom of the screen
        if self.rect.y > screen_height:
            self.passed = True
            return 1  # Return 1 point earned (player loses points when enemies pass)
        else:
            return 0  # Return 0 points earned


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
# MAIN GAME LOOP (ASYNC)
# Controls the game flow, event handling, updates, and rendering
#
# Rules for the web version:
#   - Every loop that can run for more than a moment must contain
#     "await asyncio.sleep(0)" so the browser gets control back each frame.
#   - Waiting loops must ALSO call clock.tick(): without it they spin at full
#     speed, which on phones starves the audio and causes crackling.
#   - Never block (no time.sleep).
# =============================================================================

async def main():
    # These variables are shared with the classes above (TieFighter, XWing...),
    # so they must be module-level globals, not local variables of main().
    global tie_fighters, imperial_destroyers, tie_fighter_explosions
    global start_time, high_score

    # Main game running flag
    running = True

    while running:
        # ---------------------------------------------------------------------
        # GAME SETUP SECTION
        # Initialize game objects and state for a new game
        # ---------------------------------------------------------------------

        # Create player X-Wing
        x_wing = XWing()
        pointer.reset()

        # Initialize enemy lists
        tie_fighters = []
        imperial_destroyers = []

        # Initialize explosions list for Tie Fighters
        tie_fighter_explosions = []

        # Initialize explosion (None at start) for X-Wing
        x_wing_explosion = None
        x_wing_explosion_active = False

        # Create initial Tie Fighters (10 enemies)
        for i in range(10):
            tie_fighters.append(TieFighter())

        # Create initial Imperial Destroyers (3 large enemies)
        for i in range(3):
            imperial_destroyers.append(ImperialDestroyer())

        # Cached HUD text (re-rendered only when the score changes)
        hud_score_value = None
        hud_score_surface = None
        hud_high_surface = font_20.render(f"High Score: {high_score}", True, (255, 255, 0))

        # Game state flags
        game_over = False
        pygame.mixer.music.play(loops=-1)  # Start background music looping
        initial = True  # Flag for initial start screen

        # ---------------------------------------------------------------------
        # GAME PLAY LOOP
        # Runs until player loses (game_over = True)
        # ---------------------------------------------------------------------

        while not game_over:

            # =================================================================
            # START SCREEN HANDLING
            # Displays instructions and waits for player to start
            # =================================================================

            if initial:
                # Draw background
                screen.blit(background_image, (0, 0))

                # Draw game title at top
                message1 = font_40.render("Destroy Tie Fighters or Die", True, (0, 0, 255))
                screen.blit(message1, (screen_width / 2 - message1.get_width() / 2, 50))

                # Draw X-Wing welcome image below title
                welcome_rect = x_wing_welcome_image.get_rect()
                welcome_rect.center = (screen_width / 2, screen_height / 2.5)
                screen.blit(x_wing_welcome_image, welcome_rect)

                # Draw game instructions (keyboard AND touch)
                lines = [
                    "Keyboard: Arrow keys to move, Space or Left Ctrl to fire",
                    "Touch: drag to move, X-Wing fires while you touch",
                    "Press Esc to end the game",
                    "Tap the screen or press any key to start",
                ]
                y = screen_height / 2 + 90
                for text in lines:
                    surf = font_20.render(text, True, (255, 255, 255))
                    screen.blit(surf, (screen_width / 2 - surf.get_width() / 2, y))
                    y += 35

                pygame.display.update()

                # Wait for a key press or a tap to start the game
                waiting_for_start = True
                while waiting_for_start:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            game_over = True
                            waiting_for_start = False
                        elif event.type == pygame.KEYDOWN:
                            waiting_for_start = False
                            initial = False
                        else:
                            action = pointer.handle(event)
                            if action and action[0] == 'down':
                                waiting_for_start = False
                                initial = False
                    clock.tick(30)               # <-- keeps CPU/audio healthy on phones
                    await asyncio.sleep(0)       # <-- IMPORTANT for the web

                # If the finger that started the game is still down, start firing
                x_wing.touch_firing = pointer.down
                continue  # Skip the rest of the frame

            # =================================================================
            # EVENT HANDLING SECTION
            # Processes keyboard, touch and window events
            # =================================================================

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
                    elif event.key == pygame.K_LCTRL or event.key == pygame.K_SPACE:
                        x_wing.firing = True

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
                    elif event.key == pygame.K_LCTRL or event.key == pygame.K_SPACE:
                        x_wing.firing = False

                else:
                    # Touch screen (or mouse drag)
                    action = pointer.handle(event)
                    if action:
                        kind, dx, dy = action
                        if kind == 'down':
                            x_wing.touch_firing = True
                        elif kind == 'move':
                            x_wing.drag(dx, dy)
                        elif kind == 'up':
                            x_wing.touch_firing = False

            # =================================================================
            # GAME LOGIC UPDATES SECTION
            # Updates all game objects and handles collisions
            # =================================================================

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
                        tie_fighters.append(TieFighter())
                        play_tie_sound()

                    # Check for collision between X-Wing and Tie Fighter
                    if x_wing.rect.colliderect(tie_fighter.rect):
                        x_wing_explosion = Explosion(x_wing.rect.centerx, x_wing.rect.centery)
                        x_wing_explosion_active = True
                        x_wing.can_move = False  # Stop X-Wing movement
                        collision_sound.play()
                        break  # Exit loop to prevent multiple explosions

                # Update all Imperial Destroyers
                for imperial_destroyer in imperial_destroyers[:]:
                    imperial_destroyer.update()

                    # Handle Imperial Destroyers that have passed the bottom of the screen
                    if imperial_destroyer.rect.y > screen_height:
                        imperial_destroyers.remove(imperial_destroyer)
                        imperial_destroyers.append(ImperialDestroyer())

                    # Check for collision between X-Wing and Imperial Destroyer
                    if x_wing.rect.colliderect(imperial_destroyer.rect):
                        x_wing_explosion = Explosion(x_wing.rect.centerx, x_wing.rect.centery)
                        x_wing_explosion_active = True
                        x_wing.can_move = False  # Stop X-Wing movement
                        collision_sound.play()
                        break  # Exit loop to prevent multiple explosions

                # Update X-Wing position and bullets
                x_wing.update()

            # =================================================================
            # RENDERING SECTION
            # Draws all game objects to the screen
            # =================================================================

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

            # Draw current score in the top-left corner (cached until it changes)
            if hud_score_value != x_wing.score:
                hud_score_value = x_wing.score
                hud_score_surface = font_20.render("Score: " + str(x_wing.score), True, (255, 255, 255))
            screen.blit(hud_score_surface, (10, 10))

            # Draw high score below current score
            screen.blit(hud_high_surface, (10, 40))

            if DEBUG_TOUCH:
                dbg = font_20.render(
                    f"touch down={pointer.down} last={pointer.last_event_name} firing={x_wing.touch_firing}",
                    True, (0, 255, 0))
                screen.blit(dbg, (10, 70))

            # Update the display
            pygame.display.update()

            # Control game speed (60 FPS)
            clock.tick(60)

            # Give control back to the browser once per frame
            await asyncio.sleep(0)  # <-- IMPORTANT for the web

        # =====================================================================
        # GAME OVER SECTION
        # Handles game over screen, score display, and restart/exit options
        # =====================================================================

        # Display game over screen
        screen.fill((0, 0, 0))

        # Display Darth Vader image above text (centered at top of screen)
        vader_rect = darth_vader_image.get_rect()
        vader_rect.center = (screen_width / 2, screen_height / 3)
        screen.blit(darth_vader_image, vader_rect)

        # Display Game Over text below Darth Vader
        game_over_text = font_60.render("Game Over", True, (255, 0, 0))
        game_over_rect = game_over_text.get_rect()
        game_over_rect.center = (screen_width / 2, screen_height / 2 + 100)
        screen.blit(game_over_text, game_over_rect)

        # Fade out sounds
        pygame.mixer.music.stop()
        tie_sound.fadeout(1000)

        # Update high score if current score is higher
        if x_wing.score > high_score:
            high_score = x_wing.score

        # Save high score
        save_high_score(high_score)

        # Display high score on game over screen
        high_score_text = font_20.render(f"High Score: {high_score}", True, (255, 255, 0))
        high_score_rect = high_score_text.get_rect()
        high_score_rect.center = (screen_width / 2, screen_height / 2 + 160)
        screen.blit(high_score_text, high_score_rect)

        # Display player's score on game over screen
        score_text = font_20.render(f"Your Score: {x_wing.score}", True, (255, 255, 255))
        score_rect = score_text.get_rect()
        score_rect.center = (screen_width / 2, screen_height / 2 + 190)
        screen.blit(score_text, score_rect)

        # Display restart/exit instructions (keyboard AND touch)
        message = font_25.render("Tap or press any key to restart  (Esc to exit)", True, (255, 255, 255))
        screen.blit(message, (screen_width / 2 - message.get_width() / 2, screen_height - 50))

        # One single display update for the whole game over screen
        pygame.display.update()

        # Wait 1 second before allowing restart (so a frantic last tap
        # doesn't skip the game over screen)
        wait_start_time = time.time()
        waiting_for_restart = True

        while waiting_for_restart:
            restart_allowed = (time.time() - wait_start_time) >= 1.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    waiting_for_restart = False
                elif event.type == pygame.KEYDOWN:
                    if restart_allowed:
                        if event.key == pygame.K_ESCAPE:
                            running = False
                        else:
                            # Reset game state for a new game
                            start_time = time.time()
                        waiting_for_restart = False
                else:
                    action = pointer.handle(event)
                    if action and action[0] == 'down' and restart_allowed:
                        start_time = time.time()
                        waiting_for_restart = False

            clock.tick(30)               # <-- keeps CPU/audio healthy on phones
            await asyncio.sleep(0)       # <-- IMPORTANT for the web

        # Clean up and exit if player chose to quit
        if not running:
            pygame.mixer.quit()
            pygame.quit()


# =============================================================================
# PROGRAM ENTRY POINT
# =============================================================================

asyncio.run(main())
