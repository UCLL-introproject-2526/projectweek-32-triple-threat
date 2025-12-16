import pygame
import random
import sys
import math
import os

# --- PAD CONFIGURATIE ---
BASE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
SOUND_DIR = os.path.join(BASE_DIR, "sound")

def load_image(name):
    path = os.path.join(ASSETS_DIR, name)
    try:
        return pygame.image.load(path).convert_alpha()
    except FileNotFoundError:
        surf = pygame.Surface((50, 50))
        surf.fill((255, 0, 255))
        return surf

def load_sound(name):
    path = os.path.join(SOUND_DIR, name)
    try:
        return pygame.mixer.Sound(path)
    except FileNotFoundError:
        return None

# --- INITIALISATIE ---
pygame.init()
pygame.mixer.init()

# Scherm
W, H = 1024, 768
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Triple Threat - Balanced")
clock = pygame.time.Clock()

# Fonts
FONT = pygame.font.SysFont("Arial", 24, bold=True)
BIG_FONT = pygame.font.SysFont("Arial", 64, bold=True)
BUTTON_FONT = pygame.font.SysFont("Arial", 36, bold=True)

# --- ASSETS ---
IMG_PLAYER = pygame.transform.rotate(load_image("race-car.png"), 90)
ENEMY_FILENAMES = ["enemy-car-1.png", "enemy-car-2.png", "enemy-car-3.png", "enemy-car-4.png"]
IMG_ENEMIES = [pygame.transform.rotate(load_image(f), 0) for f in ENEMY_FILENAMES]
IMG_FALLBACK_ENEMY = pygame.transform.rotate(load_image("car.png"), 0)

try:
    poster_path = os.path.join(ASSETS_DIR, "poster.jpg")
    IMG_POSTER = pygame.image.load(poster_path).convert()
    IMG_POSTER = pygame.transform.smoothscale(IMG_POSTER, (W, H))
except Exception:
    IMG_POSTER = None

SOUND_ENGINE = load_sound("car-effect1.mp3") 
MUSIC_PATH = os.path.join(SOUND_DIR, "Soundtrack.mp3")

if SOUND_ENGINE:
    SOUND_ENGINE.set_volume(0.3)

SCALE_CACHE = {}

# --- GAME CONSTANTEN ---
LANES = 3
ROAD_NEAR_Y = H - 40
ROAD_FAR_Y = 120
ROAD_NEAR_W = int(W * 0.85)
ROAD_FAR_W = int(W * 0.15)
ROAD_CENTER_X = W // 2
Z_SPAWN_MIN = 0.03
Z_SPAWN_MAX = 0.20

# --- HULPFUNCTIES ---
def clamp(x, a, b): return max(a, min(b, x))
def lerp(a, b, t): return a + (b - a) * t
def ease_in(t): return t * t

def road_edges_at_y(y):
    t = (y - ROAD_FAR_Y) / (ROAD_NEAR_Y - ROAD_FAR_Y)
    t = clamp(t, 0.0, 1.0)
    half_w = lerp(ROAD_FAR_W / 2, ROAD_NEAR_W / 2, t)
    return ROAD_CENTER_X - half_w, ROAD_CENTER_X + half_w

def y_from_z(z):
    z = clamp(z, 0.0, 1.0)
    t = ease_in(z)
    return lerp(ROAD_FAR_Y, ROAD_NEAR_Y, t)

def lane_center_x_at_y(lane_idx, y):
    left, right = road_edges_at_y(y)
    lane_w = (right - left) / LANES
    return left + lane_w * (lane_idx + 0.5)

def scale_cached(img, size, cache):
    key = (id(img), size[0], size[1])
    if key not in cache:
        cache[key] = pygame.transform.smoothscale(img, size)
    return cache[key]

def draw_text_with_outline(surf, text, font, color, pos):
    outline_color = (0, 0, 0)
    render_base = font.render(text, True, color)
    render_outline = font.render(text, True, outline_color)
    x, y = pos
    surf.blit(render_outline, (x-2, y))
    surf.blit(render_outline, (x+2, y))
    surf.blit(render_outline, (x, y-2))
    surf.blit(render_outline, (x, y+2))
    surf.blit(render_base, (x, y))

def draw_shadow(surf, rect, alpha=100):
    shadow_surf = pygame.Surface((rect.width, rect.height // 4), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, alpha), shadow_surf.get_rect())
    surf.blit(shadow_surf, (rect.x, rect.bottom - rect.height // 6))


# --- TEKEN OMGEVING ---
def draw_background_and_terrain(surf, t_scroll):
    for y in range(H):
        c = int(40 * (y/H))
        pygame.draw.line(surf, (20, 10, 40 + c), (0, y), (W, y))

    hill_y = ROAD_FAR_Y + 5
    pts = [(0, H), (0, hill_y)]
    for x in range(0, W + 1, 40):
        y = hill_y + int(20 * math.sin((x * 0.005) + 1.0))
        pts.append((x, y))
    pts.append((W, H))
    pygame.draw.polygon(surf, (10, 5, 15), pts)

    bands = 40
    for i in range(bands):
        t0 = i / bands
        t1 = (i + 1) / bands
        y0 = lerp(ROAD_FAR_Y, ROAD_NEAR_Y, t0)
        y1 = lerp(ROAD_FAR_Y, ROAD_NEAR_Y, t1)
        left0, right0 = road_edges_at_y(y0)
        left1, right1 = road_edges_at_y(y1)
        stripe = int(((t0 + t_scroll) * 20) % 2)
        col_base = 20 + stripe * 5
        col = (col_base, col_base + 5, col_base + 10)
        left_poly = [(0, y0), (left0, y0), (left1, y1), (0, y1)]
        right_poly = [(right0, y0), (W, y0), (W, y1), (right1, y1)]
        pygame.draw.polygon(surf, col, left_poly)
        pygame.draw.polygon(surf, col, right_poly)

def draw_road(surf, dash_offset=0.0):
    far_left = ROAD_CENTER_X - ROAD_FAR_W // 2
    far_right = ROAD_CENTER_X + ROAD_FAR_W // 2
    near_left = ROAD_CENTER_X - ROAD_NEAR_W // 2
    near_right = ROAD_CENTER_X + ROAD_NEAR_W // 2
    road_poly = [(far_left, ROAD_FAR_Y), (far_right, ROAD_FAR_Y),
                 (near_right, ROAD_NEAR_Y), (near_left, ROAD_NEAR_Y)]
    
    pygame.draw.polygon(surf, (40, 40, 50), road_poly)
    s = pygame.Surface((W,H), pygame.SRCALPHA)
    pygame.draw.lines(s, (0, 255, 255, 50), True, road_poly, 10)
    surf.blit(s, (0,0))
    pygame.draw.lines(surf, (0, 200, 255), True, road_poly, 3)

    for i in range(1, LANES):
        far_lane_w = ROAD_FAR_W / LANES
        near_lane_w = ROAD_NEAR_W / LANES
        x_far = (ROAD_CENTER_X - ROAD_FAR_W / 2) + far_lane_w * i
        x_near = (ROAD_CENTER_X - ROAD_NEAR_W / 2) + near_lane_w * i
        pygame.draw.line(surf, (70, 70, 80), (x_far, ROAD_FAR_Y), (x_near, ROAD_NEAR_Y), 1)

    dash_count = 12
    for lane_i in range(1, LANES):
        far_lane_w = ROAD_FAR_W / LANES
        near_lane_w = ROAD_NEAR_W / LANES
        x_far_base = (ROAD_CENTER_X - ROAD_FAR_W / 2) + far_lane_w * lane_i
        x_near_base = (ROAD_CENTER_X - ROAD_NEAR_W / 2) + near_lane_w * lane_i
        
        for k in range(dash_count):
            t0 = ((k / dash_count) + dash_offset) % 1.0
            t1 = ((k + 0.5) / dash_count + dash_offset) % 1.0
            if t1 < t0: continue
            
            y0 = lerp(ROAD_FAR_Y, ROAD_NEAR_Y, t0)
            y1 = lerp(ROAD_FAR_Y, ROAD_NEAR_Y, t1)
            x0 = lerp(x_far_base, x_near_base, t0)
            x1 = lerp(x_far_base, x_near_base, t1)
            
            alpha = int(lerp(100, 255, t0))
            col = (alpha, alpha, alpha)
            pygame.draw.line(surf, col, (x0, y0), (x1, y1), 3)

def draw_button(surf, rect, text, hover_color=(100, 200, 255), default_color=(0, 150, 255)):
    mouse_pos = pygame.mouse.get_pos()
    is_hovering = rect.collidepoint(mouse_pos)
    color = hover_color if is_hovering else default_color
    
    shadow_rect = rect.copy()
    shadow_rect.y += 4
    pygame.draw.rect(surf, (0,0,0,100), shadow_rect, border_radius=15)
    
    pygame.draw.rect(surf, color, rect, border_radius=15)
    pygame.draw.rect(surf, (255, 255, 255), rect, 3, border_radius=15)
    
    text_surf = BUTTON_FONT.render(text, True, (255, 255, 255))
    text_rect = text_surf.get_rect(center=rect.center)
    surf.blit(text_surf, text_rect)

# --- PARTICLES ---
class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.size = random.randint(4, 8)
        self.color = color
        self.life = 20
        self.vx = random.uniform(-1, 1)
        self.vy = random.uniform(2, 5)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        self.size = max(0, self.size - 0.2)

    def draw(self, surf):
        if self.life > 0 and self.size > 0:
            s = pygame.Surface((int(self.size)*2, int(self.size)*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, 150), (int(self.size), int(self.size)), int(self.size))
            surf.blit(s, (int(self.x), int(self.y)))


# --- CLASSES ---
class Player:
    def __init__(self):
        self.lane = 1
        self.target_lane = 1
        self.lane_blend = 1.0 
        self.lane_change_speed = 0.12
        self.z = 0.92
        self.base_w = 80
        self.base_h = 110
        self.angle = 0
        self.particles = []

    def move_left(self):
        self.target_lane = max(0, self.target_lane - 1)

    def move_right(self):
        self.target_lane = min(LANES - 1, self.target_lane + 1)

    def update(self, boosting):
        if self.lane != self.target_lane:
            self.lane_blend += self.lane_change_speed
            tilt_direction = -1 if self.target_lane < self.lane else 1
            self.angle = lerp(self.angle, tilt_direction * -15, 0.2) 

            if self.lane_blend >= 1.0:
                self.lane = self.target_lane
                self.lane_blend = 1.0
        else:
            self.lane_blend = 1.0
            self.angle = lerp(self.angle, 0, 0.2)

        if boosting:
            rect = self.get_rect_no_rotate()
            p_color = (0, 255, 255) if random.random() < 0.5 else (255, 200, 50)
            self.particles.append(Particle(rect.centerx + random.randint(-10, 10), rect.bottom - 10, p_color))
        
        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

    def get_rect_no_rotate(self):
        y = y_from_z(self.z)
        if self.lane != self.target_lane:
            x_from = lane_center_x_at_y(self.lane, y)
            x_to = lane_center_x_at_y(self.target_lane, y)
            x = lerp(x_from, x_to, clamp(self.lane_blend, 0.0, 1.0))
        else:
            x = lane_center_x_at_y(self.lane, y)
        scale = lerp(0.35, 1.12, self.z)
        w = int(self.base_w * scale)
        h = int(self.base_h * scale)
        rect = pygame.Rect(0, 0, w, h)
        rect.centerx = int(x)
        rect.bottom = int(y)
        return rect

    def get_rect(self):
        return self.get_rect_no_rotate()

    def draw(self, surf):
        for p in self.particles:
            p.draw(surf)

        r = self.get_rect_no_rotate()
        draw_shadow(surf, r)
        img = scale_cached(IMG_PLAYER, (r.w, r.h), SCALE_CACHE)
        if abs(self.angle) > 1:
            img = pygame.transform.rotate(img, self.angle)
            new_rect = img.get_rect(center=r.center)
            surf.blit(img, new_rect.topleft)
        else:
            surf.blit(img, r.topleft)

class Obstacle:
    def __init__(self, lane, z, kind="car", sprite=None):
        self.lane = lane
        self.z = z
        self.kind = kind
        self.sprite = sprite
        self.base_w = 75
        self.base_h = 145
        if kind == "roadblock":
            self.base_w = 150
            self.base_h = 65
        elif kind == "cone":
            self.base_w = 34
            self.base_h = 34

    def update(self, dz):
        self.z += dz

    def get_rect(self):
        y = y_from_z(self.z)
        scale = lerp(0.22, 1.18, self.z)
        w = int(self.base_w * scale)
        h = int(self.base_h * scale)
        if self.kind == "roadblock":
            x0 = lane_center_x_at_y(self.lane, y)
            x1 = lane_center_x_at_y(self.lane + 1, y)
            x = (x0 + x1) * 0.5
            lane_w = (road_edges_at_y(y)[1] - road_edges_at_y(y)[0]) / LANES
            w = int(lane_w * 2 * 0.95 * scale)
        else:
            x = lane_center_x_at_y(self.lane, y)
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (int(x), int(y - h * 0.10))
        return rect

    def draw(self, surf):
        r = self.get_rect()
        draw_shadow(surf, r)

        if self.kind == "car":
            car_img = self.sprite if self.sprite else IMG_FALLBACK_ENEMY
            img = scale_cached(car_img, (r.w, r.h), SCALE_CACHE)
            surf.blit(img, r.topleft)
        elif self.kind == "roadblock":
            pygame.draw.rect(surf, (255, 200, 0), r, border_radius=5)
            pygame.draw.rect(surf, (50,50,50), r, 2, border_radius=5)
            for i in range(0, r.w, 20):
                p1 = (r.left + i, r.bottom)
                p2 = (r.left + i + 10, r.top)
                if p2[0] < r.right:
                    pygame.draw.line(surf, (0,0,0), p1, p2, 6)
        elif self.kind == "cone":
            pygame.draw.rect(surf, (255, 100, 0), r)
            mid_rect = pygame.Rect(r.x + 2, r.y + r.h//3, r.w - 4, r.h//3)
            pygame.draw.rect(surf, (255, 255, 255), mid_rect)

def choose_spawn_pattern(obstacles, z_spawn):
    occupied_lanes = []
    for o in obstacles:
        if abs(o.z - z_spawn) < 0.15:
            occupied_lanes.append(o.lane)
            if o.kind == "roadblock":
                occupied_lanes.append(o.lane + 1)
    available_lanes = [l for l in range(LANES) if l not in occupied_lanes]
    if not available_lanes: return []
    
    # KANS VERLAAGD: Roadblock nu 5% kans (was 10%)
    if len(available_lanes) >= 2 and random.random() < 0.05:
        lane = random.choice(available_lanes[:-1]) 
        if (lane + 1) in available_lanes: return [(lane, "roadblock")]
    
    # KANS VERLAAGD: 2 auto's nu 10% kans (was 30%)
    count = 2 if (len(available_lanes) > 1 and random.random() < 0.1) else 1
    
    chosen = random.sample(available_lanes, count)
    new_obs = []
    for l in chosen:
        kind = "cone" if random.random() < 0.2 else "car"
        new_obs.append((l, kind))
    return new_obs

# --- MAIN ---
def main():
    player = Player()
    obstacles = []
    
    score = 0
    alive = True
    paused = False
    started = False
    
    # BALANS AANPASSINGEN
    base_speed = 0.0015         # START SNELHEID VERLAAGD (50% trager)
    speed_ramp = 0.0000002      # VERSNELLING VERLAAGD (5x trager)
    speed = base_speed
    
    dash_offset = 0.0
    spawn_progress = 0.0
    spawn_threshold = 0.45      # SPAWN AFSTAND VERGROOT (Meer ruimte)
    
    if os.path.exists(MUSIC_PATH):
        try:
            pygame.mixer.music.load(MUSIC_PATH)
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(-1) 
        except: pass

    enemy_cycle_i = 0

    btn_w, btn_h = 175, 50
    center_x = W // 2 - btn_w // 2
    btn_play = pygame.Rect(center_x, H // 2 - 20, btn_w, btn_h)
    btn_quit_menu = pygame.Rect(center_x, H // 2 + 70, btn_w, btn_h)
    btn_restart = pygame.Rect(center_x, H // 2 + 20, btn_w, btn_h)
    btn_quit_over = pygame.Rect(center_x, H // 2 + 100, btn_w, btn_h)

    while True:
        dt = clock.tick(60)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if not started:
                    if btn_play.collidepoint(event.pos): started = True
                    if btn_quit_menu.collidepoint(event.pos): pygame.quit(); sys.exit()
                elif not alive:
                    if btn_restart.collidepoint(event.pos): main()
                    if btn_quit_over.collidepoint(event.pos): pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q: pygame.quit(); sys.exit()
                if not started:
                    if event.key == pygame.K_SPACE: started = True
                elif alive:
                    if event.key == pygame.K_ESCAPE: paused = not paused
                    if not paused:
                        if event.key in (pygame.K_LEFT, pygame.K_a): player.move_left()
                        if event.key in (pygame.K_RIGHT, pygame.K_d): player.move_right()
                else: 
                    if event.key == pygame.K_r: main() 

        keys = pygame.key.get_pressed()
        if started and alive and not paused:
            boosting = keys[pygame.K_UP] or keys[pygame.K_w]
            braking = keys[pygame.K_DOWN] or keys[pygame.K_s]
            
            target_speed = base_speed * 1.5 if boosting else (base_speed * 0.7 if braking else base_speed)
            speed = lerp(speed, target_speed, 0.1)
            
            if SOUND_ENGINE:
                if boosting and alive:
                    if SOUND_ENGINE.get_num_channels() == 0: SOUND_ENGINE.play(-1)
                else: SOUND_ENGINE.stop()

            player.update(boosting)
            
            score += 1 + int(speed * 1000)
            base_speed += speed_ramp * dt # Langzamere opbouw
            
            spawn_progress += speed
            if spawn_progress > spawn_threshold: 
                spawn_progress = 0
                z_spawn = Z_SPAWN_MIN
                pattern = choose_spawn_pattern(obstacles, z_spawn)
                for lane, kind in pattern:
                    sprite = None
                    if kind == "car":
                        sprite = IMG_ENEMIES[enemy_cycle_i]
                        enemy_cycle_i = (enemy_cycle_i + 1) % len(IMG_ENEMIES)
                    obstacles.append(Obstacle(lane, z_spawn, kind, sprite))

            p_rect = player.get_rect()
            for obs in obstacles[:]: 
                obs.update(speed)
                if obs.z > 1.2: obstacles.remove(obs); continue
                if obs.z > 0.85 and obs.z < 1.0:
                    o_rect = obs.get_rect()
                    hitbox = o_rect.inflate(-15, -15) 
                    if p_rect.colliderect(hitbox):
                        alive = False
                        if SOUND_ENGINE: SOUND_ENGINE.stop()
            dash_offset = (dash_offset + speed * 2.0) % 1.0

        if not started:
            if IMG_POSTER: screen.blit(IMG_POSTER, (0,0))
            else: screen.fill((0,0,0))
            s = pygame.Surface((W,H), pygame.SRCALPHA); s.fill((0,0,0,80))
            screen.blit(s, (0,0))
            draw_button(screen, btn_play, "PLAY")
            draw_button(screen, btn_quit_menu, "QUIT", hover_color=(255, 100, 100), default_color=(200, 50, 50))

        else:
            frame = pygame.Surface((W, H))
            draw_background_and_terrain(frame, dash_offset)
            draw_road(frame, dash_offset)
            obstacles.sort(key=lambda o: -o.z) 
            for obs in obstacles: obs.draw(frame)
            player.draw(frame)
            
            draw_text_with_outline(frame, f"SCORE: {score}", FONT, (255, 255, 255), (20, 20))
            
            speed_pct = min(1.0, (speed / 0.01))
            bar_w = 200
            pygame.draw.rect(frame, (50,50,50), (20, 60, bar_w, 20), border_radius=5)
            pygame.draw.rect(frame, (0,255,255), (20, 60, int(bar_w * speed_pct), 20), border_radius=5)
            draw_text_with_outline(frame, "SPEED", pygame.font.SysFont("Arial", 16), (255,255,255), (25, 62))

            if not alive:
                s = pygame.Surface((W,H), pygame.SRCALPHA); s.fill((50,0,0,200))
                frame.blit(s, (0,0))
                txt = BIG_FONT.render("CRASHED!", True, (255, 50, 50))
                frame.blit(txt, (W//2 - txt.get_width()//2, H//2 - 80))
                draw_button(frame, btn_restart, "RESTART")
                draw_button(frame, btn_quit_over, "QUIT", hover_color=(255, 100, 100), default_color=(200, 50, 50))
            
            elif paused:
                s = pygame.Surface((W,H), pygame.SRCALPHA); s.fill((0,0,0,150))
                frame.blit(s, (0,0))
                txt = BIG_FONT.render("PAUZE", True, (255, 255, 255))
                frame.blit(txt, (W//2 - txt.get_width()//2, H//2))

            screen.blit(frame, (0,0))

        pygame.display.flip()

if __name__ == "__main__":
    main()