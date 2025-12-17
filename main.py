import pygame
import random
import sys
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
        surf = pygame.Surface((50, 50), pygame.SRCALPHA)
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

W, H = 1024, 768
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Triple Threat - Final Version")
clock = pygame.time.Clock()

# --- FONTS ---
FONT = pygame.font.SysFont("Arial", 22, bold=True)
BIG_FONT = pygame.font.SysFont("Arial", 64, bold=True)
COUNTDOWN_FONT = pygame.font.SysFont("Arial", 120, bold=True)
BUTTON_FONT = pygame.font.SysFont("Arial", 24, bold=True)
SMALL_FONT = pygame.font.SysFont("Arial", 16, bold=True)

# --- ASSETS LADEN ---
CAR_DRIVE_1 = pygame.transform.rotate(load_image("retro_porsche.png"), 0)
CAR_DRIVE_2 = pygame.transform.rotate(load_image("backviewbmwm3.png"), 0)
CAR_DRIVE_3 = pygame.transform.rotate(load_image("backview_skyline.png"), 0)
PLAYER_DRIVE_SPRITES = [CAR_DRIVE_1, CAR_DRIVE_2, CAR_DRIVE_3]

MENU_CAR_1 = CAR_DRIVE_1
MENU_CAR_2 = CAR_DRIVE_2
MENU_CAR_3 = CAR_DRIVE_3
PLAYER_MENU_VIEWS = [MENU_CAR_1, MENU_CAR_2, MENU_CAR_3]

ENEMY_FILENAMES = ["kart.png", "front_view.png", "sport_car.png", "bmw.png", "bmw2.png", "front_view_skyline_enemy.png", "Bmwm3gtr.png"]
IMG_ENEMIES = [pygame.transform.rotate(load_image(f), 0) for f in ENEMY_FILENAMES]
IMG_FALLBACK_ENEMY = pygame.transform.rotate(load_image("car.png"), 0)

# optional mag icon for ammo HUD
MAG_ICON = load_image("ammo.png")

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

EXPLOSION_FRAMES = []
for i in range(1, 11):
    img = load_image(f"explosion/explosion-c{i}.png")
    EXPLOSION_FRAMES.append(img)

# --- CONSTANTEN ---
LANES = 3
ROAD_NEAR_Y = H
ROAD_FAR_Y = 160
ROAD_NEAR_W = int(W * 0.95)
ROAD_FAR_W = int(W * 0.15)
ROAD_CENTER_X = W // 2
Z_SPAWN_MIN = 0.03
Z_SPAWN_MAX = 0.20

# car HP
CAR_MAX_HP = 5

# ammo
MAG_SIZE = 12
RELOAD_TIME = 180  # frames (~3.0s @ 60fps)

# KLEUREN
NEON_CYAN = (0, 255, 255)
NEON_RED = (255, 50, 50)
WHITE = (255, 255, 255)
KERB_RED = (200, 0, 0)
KERB_WHITE = (230, 230, 230)

# --- HULPFUNCTIES ---
def clamp(x, a, b): return max(a, min(b, x))
def lerp(a, b, t): return a + (b - a) * t
def ease_in(t): return t * t

def road_edges_at_y(y):
    t = (y - ROAD_FAR_Y) / (ROAD_NEAR_Y - ROAD_FAR_Y)
    if t < 0: t = 0
    half_w = lerp(ROAD_FAR_W / 2, ROAD_NEAR_W / 2, t)
    return ROAD_CENTER_X - half_w, ROAD_CENTER_X + half_w

def y_from_z(z):
    if z < 0: z = 0
    t = ease_in(z)
    return lerp(ROAD_FAR_Y, ROAD_NEAR_Y, t)

def lane_center_x_at_y(lane_idx, y):
    left, right = road_edges_at_y(y)
    lane_w = (right - left) / LANES
    return left + lane_w * (lane_idx + 0.5)

def scale_cached(img, size, cache):
    w, h = max(1, int(size[0])), max(1, int(size[1]))
    key = (id(img), w, h)
    if key not in cache:
        cache[key] = pygame.transform.smoothscale(img, (w, h))
    return cache[key]

def draw_text_with_outline(surf, text, font, color, pos, center=False):
    outline_color = (0, 0, 0)
    render_base = font.render(text, True, color)
    render_outline = font.render(text, True, outline_color)
    if center:
        rect = render_base.get_rect(center=pos)
        x, y = rect.topleft
    else:
        x, y = pos
    surf.blit(render_outline, (x-2, y))
    surf.blit(render_outline, (x+2, y))
    surf.blit(render_outline, (x, y-2))
    surf.blit(render_outline, (x, y+2))
    surf.blit(render_base, (x, y))

def draw_shadow(surf, rect, alpha=100):
    if rect.width <= 0 or rect.height <= 0: return
    shadow_surf = pygame.Surface((rect.width, max(1, rect.height // 4)), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, alpha), shadow_surf.get_rect())
    surf.blit(shadow_surf, (rect.x, rect.bottom - rect.height // 6))

def draw_button(surf, rect, text, is_danger=False):
    mouse_pos = pygame.mouse.get_pos()
    is_hovering = rect.collidepoint(mouse_pos)
    shadow_rect = rect.copy(); shadow_rect.y += 4
    s_shadow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(s_shadow, (0, 0, 0, 100), s_shadow.get_rect(), border_radius=10)
    surf.blit(s_shadow, shadow_rect.topleft)

    s_body = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    if is_danger:
        bg_color = (220, 20, 20, 230) if is_hovering else (160, 0, 0, 200)
        border_color = (255, 100, 100) if is_hovering else (200, 50, 50)
    else:
        bg_color = (0, 180, 255, 230) if is_hovering else (0, 100, 180, 200)
        border_color = (150, 255, 255) if is_hovering else (0, 200, 255)

    pygame.draw.rect(s_body, bg_color, s_body.get_rect(), border_radius=10)
    surf.blit(s_body, rect.topleft)
    g = pygame.Surface((rect.width, rect.height // 2), pygame.SRCALPHA)
    pygame.draw.rect(g, (255, 255, 255, 30), g.get_rect(), border_top_left_radius=10, border_top_right_radius=10)
    surf.blit(g, rect.topleft)
    pygame.draw.rect(surf, border_color, rect, 2, border_radius=10)

    text_surf = BUTTON_FONT.render(text, True, WHITE)
    text_rect = text_surf.get_rect(center=rect.center)
    text_shadow = BUTTON_FONT.render(text, True, (0, 0, 0))
    surf.blit(text_shadow, (text_rect.x + 1, text_rect.y + 1))
    surf.blit(text_surf, text_rect)

# --- HORIZONTAAL STOPLICHT ---
def draw_countdown_lights(surf, stage):
    center_x = W // 2
    center_y = H // 4

    if stage == 0:
        offset_x = random.randint(-3, 3)
        offset_y = random.randint(-3, 3)
        txt_surf = COUNTDOWN_FONT.render("GO!", True, NEON_CYAN)
        shadow_surf = COUNTDOWN_FONT.render("GO!", True, (0, 50, 100))
        txt_rect = txt_surf.get_rect(center=(center_x, H // 2))
        surf.blit(shadow_surf, (txt_rect.x + offset_x + 4, txt_rect.y + offset_y + 4))
        surf.blit(txt_surf, (txt_rect.x + offset_x, txt_rect.y + offset_y))
        return

    box_w, box_h = 220, 80
    box_rect = pygame.Rect(0, 0, box_w, box_h)
    box_rect.center = (center_x, center_y)

    pygame.draw.rect(surf, (20, 22, 25), box_rect, border_radius=20)
    pygame.draw.rect(surf, (160, 170, 180), box_rect, 4, border_radius=20)
    pygame.draw.rect(surf, (10, 10, 10), box_rect.inflate(-6, -6), 2, border_radius=18)

    bolt_offset = 12
    for bx in [box_rect.left + bolt_offset, box_rect.right - bolt_offset]:
        for by in [box_rect.top + bolt_offset, box_rect.bottom - bolt_offset]:
            pygame.draw.circle(surf, (100, 100, 100), (bx, by), 3)

    radius = 22
    spacing = 65
    colors = {
        3: {"lit": (255, 20, 20),   "dark": (60, 10, 10),   "glow": (255, 0, 0)},
        2: {"lit": (255, 180, 0),   "dark": (60, 40, 0),    "glow": (255, 140, 0)},
        1: {"lit": (0, 255, 80),    "dark": (0, 60, 20),    "glow": (0, 255, 0)}
    }
    current_set = colors.get(stage, colors[3])

    positions = [
        (center_x - spacing, center_y),
        (center_x, center_y),
        (center_x + spacing, center_y)
    ]

    for x, y in positions:
        pygame.draw.circle(surf, (5, 5, 5), (x, y), radius + 4)
        pygame.draw.circle(surf, (80, 80, 90), (x, y), radius + 4, 2)

        glow_radius = int(radius * 1)
        glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        glow_rgb = current_set["glow"]
        pygame.draw.circle(glow_surf, (*glow_rgb, 30), (glow_radius, glow_radius), glow_radius)
        pygame.draw.circle(glow_surf, (*glow_rgb, 60), (glow_radius, glow_radius), int(radius * 0.8))
        surf.blit(glow_surf, (x - glow_radius, y - glow_radius), special_flags=pygame.BLEND_ADD)

        main_color = current_set["lit"]
        pygame.draw.circle(surf, main_color, (x, y), radius)
        pygame.draw.circle(surf, [min(255, c + 50) for c in main_color], (x, y), int(radius * 0.7))

        shine_rect = pygame.Rect(x - radius * 0.5, y - radius * 0.6, radius * 0.4, radius * 0.25)
        pygame.draw.ellipse(surf, (255, 255, 255, 180), shine_rect)

# --- SKYLINE GENERATIE ---
skyline_segments = []
num_buildings = 60
bg_width = W // num_buildings + 1
for _ in range(num_buildings + 5):
    skyline_segments.append(random.randint(30, 150))

stars = []
for _ in range(50):
    stars.append((random.randint(0, W), random.randint(0, ROAD_FAR_Y)))

def draw_background_and_terrain(surf, t_scroll):
    for y in range(H):
        c = int(50 * (y/H))
        col = (10, 5 + c//2, 20 + c)
        pygame.draw.line(surf, col, (0, y), (W, y))

    for sx, sy in stars:
        if random.random() > 0.98:
            continue
        pygame.draw.circle(surf, (200, 200, 255), (sx, sy), 1)

    for i, h in enumerate(skyline_segments):
        x = i * bg_width
        rect_back = pygame.Rect(x, ROAD_FAR_Y - h, bg_width, h + 100)
        pygame.draw.rect(surf, (15, 15, 25), rect_back)

        h2 = skyline_segments[(i + 3) % len(skyline_segments)] * 0.7
        rect_front = pygame.Rect(x, ROAD_FAR_Y - h2, bg_width, h2 + 100)
        pygame.draw.rect(surf, (30, 30, 45), rect_front)

        if i % 4 == 0:
            pygame.draw.rect(surf, (255, 255, 100), (x + 2, ROAD_FAR_Y - h2 + 10, 2, 2))

    bands = 120
    for i in range(bands):
        t0 = i / bands
        t1 = (i + 1) / bands
        y0 = lerp(ROAD_FAR_Y, ROAD_NEAR_Y, t0)
        y1 = lerp(ROAD_FAR_Y, ROAD_NEAR_Y, t1)
        left0, right0 = road_edges_at_y(y0)
        left1, right1 = road_edges_at_y(y1)
        scroll_val = (t0 + t_scroll) * 15
        stripe = int(scroll_val) % 2
        c = 38 if stripe == 0 else 35
        ground_col = (c, c, c + 8)
        left_poly = [(0, y0), (left0, y0), (left1, y1), (0, y1)]
        right_poly = [(right0, y0), (W, y0), (W, y1), (right1, y1)]
        pygame.draw.polygon(surf, ground_col, left_poly)
        pygame.draw.polygon(surf, ground_col, right_poly)

def draw_road(surf, dash_offset=0.0):
    far_left = ROAD_CENTER_X - ROAD_FAR_W // 2
    far_right = ROAD_CENTER_X + ROAD_FAR_W // 2
    near_left = ROAD_CENTER_X - ROAD_NEAR_W // 2
    near_right = ROAD_CENTER_X + ROAD_NEAR_W // 2
    road_poly = [(far_left, ROAD_FAR_Y), (far_right, ROAD_FAR_Y),
                 (near_right, ROAD_NEAR_Y), (near_left, ROAD_NEAR_Y)]
    pygame.draw.polygon(surf, (40, 40, 50), road_poly)

    num_segments = 24
    for i in range(num_segments):
        t0 = i / num_segments
        t1 = (i + 1) / num_segments
        y0 = lerp(ROAD_FAR_Y, ROAD_NEAR_Y, t0)
        y1 = lerp(ROAD_FAR_Y, ROAD_NEAR_Y, t1)
        l0, r0 = road_edges_at_y(y0)
        l1, r1 = road_edges_at_y(y1)
        curb_w0 = (r0 - l0) * 0.05
        curb_w1 = (r1 - l1) * 0.05
        scroll_val = (t0 + dash_offset) * 10
        col = KERB_RED if int(scroll_val) % 2 == 0 else KERB_WHITE
        pygame.draw.polygon(surf, col, [(l0 - curb_w0, y0), (l0, y0), (l1, y1), (l1 - curb_w1, y1)])
        pygame.draw.polygon(surf, col, [(r0, y0), (r0 + curb_w0, y0), (r1 + curb_w1, y1), (r1, y1)])

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
            if t1 < t0:
                continue
            y0 = lerp(ROAD_FAR_Y, ROAD_NEAR_Y, t0)
            y1 = lerp(ROAD_FAR_Y, ROAD_NEAR_Y, t1)
            x0 = lerp(x_far_base, x_near_base, t0)
            x1 = lerp(x_far_base, x_near_base, t1)
            alpha = int(lerp(100, 255, t0))
            pygame.draw.line(surf, (alpha, alpha, alpha), (x0, y0), (x1, y1), 3)

# --- CLASSES ---
class Particle:
    def __init__(self, x, y, color):
        self.x = x; self.y = y
        self.size = random.randint(4, 8)
        self.color = color; self.life = 20
        self.vx = random.uniform(-1, 1); self.vy = random.uniform(2, 5)

    def update(self):
        self.x += self.vx; self.y += self.vy
        self.life -= 1; self.size = max(0, self.size - 0.2)

    def draw(self, surf):
        if self.life > 0 and self.size > 0:
            s = pygame.Surface((int(self.size)*2, int(self.size)*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, 150), (int(self.size), int(self.size)), int(self.size))
            surf.blit(s, (int(self.x), int(self.y)))

class Building:
    def __init__(self, side, z):
        self.side = side
        self.z = z
        self.width_factor = random.uniform(0.8, 1.5)
        self.height_factor = random.uniform(1.5, 3.5)
        gray = random.randint(30, 60)
        self.color = (gray, gray, gray + 10)
        self.lights = []
        rows = int(self.height_factor * 3); cols = int(self.width_factor * 2)
        for r in range(rows):
            for c in range(cols):
                if random.random() > 0.4:
                    self.lights.append((c, r))

    def update(self, speed):
        self.z += speed

    def draw(self, surf):
        y = y_from_z(self.z)
        scale = lerp(0.22, 1.18, self.z)
        base_w_px = 120
        w = int(base_w_px * self.width_factor * scale)
        h = int(base_w_px * self.height_factor * scale)
        left_road, right_road = road_edges_at_y(y)
        offset_x = 15 * scale
        x = (left_road - w - offset_x) if self.side == -1 else (right_road + offset_x)
        rect = pygame.Rect(x, y - h, w, h)
        pygame.draw.rect(surf, self.color, rect)
        pygame.draw.rect(surf, (0,0,0), rect, 1)
        if self.lights:
            win_w = w // (int(self.width_factor * 2) + 1)
            win_h = h // (int(self.height_factor * 3) + 1)
            if win_w > 1 and win_h > 1:
                for c, r in self.lights:
                    wx = rect.x + c * win_w + win_w//2
                    wy = rect.y + r * win_h + win_h//2
                    win_col = (255, 220, 50) if (c+r)%3 != 0 else (0, 200, 255)
                    pygame.draw.rect(surf, win_col, (wx, wy, win_w-1, win_h-1))

class Player:
    def __init__(self, image):
        self.original_image = image
        self.lane = 1; self.target_lane = 1; self.lane_blend = 1.0
        self.lane_change_speed = 0.08
        self.z = 0.92; self.base_w = 80; self.base_h = 110; self.angle = 0
        self.particles = []

    def move_left(self):
        if self.lane == self.target_lane and self.target_lane > 0:
            self.target_lane -= 1; self.lane_blend = 0.0

    def move_right(self):
        if self.lane == self.target_lane and self.target_lane < LANES - 1:
            self.target_lane += 1; self.lane_blend = 0.0

    def update(self, boosting):
        if self.lane != self.target_lane:
            self.lane_blend += self.lane_change_speed
            tilt_direction = -1 if self.target_lane < self.lane else 1
            self.angle = lerp(self.angle, tilt_direction * -15, 0.2)
            if self.lane_blend >= 1.0:
                self.lane = self.target_lane; self.lane_blend = 1.0
        else:
            self.lane_blend = 1.0; self.angle = lerp(self.angle, 0, 0.2)

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
        w = int(self.base_w * scale); h = int(self.base_h * scale)
        rect = pygame.Rect(0, 0, w, h); rect.centerx = int(x); rect.bottom = int(y)
        return rect

    def get_rect(self):
        return self.get_rect_no_rotate()

    def draw(self, surf):
        for p in self.particles:
            p.draw(surf)
        r = self.get_rect_no_rotate()
        draw_shadow(surf, r)
        img = scale_cached(self.original_image, (r.w, r.h), SCALE_CACHE)
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

        self.hp = CAR_MAX_HP if kind == "car" else None

    def update(self, dz):
        self.z += dz

    def get_rect(self):
        y = y_from_z(self.z)
        scale = lerp(0.22, 1.18, self.z)
        w = int(self.base_w * scale); h = int(self.base_h * scale)
        if self.kind == "roadblock":
            x0 = lane_center_x_at_y(self.lane, y)
            x1 = lane_center_x_at_y(self.lane + 1, y)
            x = (x0 + x1) * 0.5
            lane_w = (road_edges_at_y(y)[1] - road_edges_at_y(y)[0]) / LANES
            w = int(lane_w * 2 * 0.95 * scale)
        else:
            x = lane_center_x_at_y(self.lane, y)
        rect = pygame.Rect(0, 0, w, h); rect.center = (int(x), int(y - h * 0.10))
        return rect

    def draw(self, surf):
        r = self.get_rect()
        draw_shadow(surf, r)

        if self.kind == "car":
            car_img = self.sprite if self.sprite else IMG_FALLBACK_ENEMY
            img = scale_cached(car_img, (r.w, r.h), SCALE_CACHE)
            surf.blit(img, r.topleft)

            if self.hp is not None:
                pct = clamp(self.hp / CAR_MAX_HP, 0.0, 1.0)
                bar_w = int(r.w * 0.60)
                bar_h = max(3, int(r.h * 0.06))
                bx = r.centerx - bar_w // 2
                by = r.y - bar_h - 2
                pygame.draw.rect(surf, (0, 0, 0), (bx, by, bar_w, bar_h), border_radius=2)
                pygame.draw.rect(surf, NEON_CYAN, (bx, by, int(bar_w * pct), bar_h), border_radius=2)

        elif self.kind == "roadblock":
            pygame.draw.rect(surf, (255, 200, 0), r, border_radius=5)
            pygame.draw.rect(surf, (50,50,50), r, 2, border_radius=5)
            for i in range(0, r.w, 20):
                p1 = (r.left + i, r.bottom); p2 = (r.left + i + 10, r.top)
                if p2[0] < r.right:
                    pygame.draw.line(surf, (0,0,0), p1, p2, 6)

        elif self.kind == "cone":
            pygame.draw.rect(surf, (255, 100, 0), r)
            mid_rect = pygame.Rect(r.x + 2, r.y + r.h//3, r.w - 4, r.h//3)
            pygame.draw.rect(surf, (255, 255, 255), mid_rect)

class Bullet:
    def __init__(self, lane, z):
        self.lane = lane
        self.z = z
        self.speed = 0.040
        self.radius = 4

    def update(self):
        self.z -= self.speed

    def get_pos(self):
        y = y_from_z(self.z)
        x = lane_center_x_at_y(self.lane, y)
        return int(x), int(y)

    def get_rect(self):
        x, y = self.get_pos()
        r = self.radius
        return pygame.Rect(x - r, y - r, r * 2, r * 2)

    def draw(self, surf):
        x, y = self.get_pos()
        pygame.draw.circle(surf, NEON_CYAN, (x, y), self.radius)
        pygame.draw.circle(surf, WHITE, (x, y), self.radius, 1)

class Explosion:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
        self.frame = 0.0
        self.frame_speed = 0.85

    def update(self):
        self.frame += self.frame_speed

    def draw(self, surf):
        idx = int(self.frame)
        if idx >= len(EXPLOSION_FRAMES):
            return
        img = EXPLOSION_FRAMES[idx]
        scale = lerp(0.35, 1.35, self.z)
        w = max(2, int(img.get_width() * scale))
        h = max(2, int(img.get_height() * scale))
        img_s = scale_cached(img, (w, h), SCALE_CACHE)
        rect = img_s.get_rect(center=(self.x, self.y))
        surf.blit(img_s, rect.topleft)

    def done(self):
        return int(self.frame) >= len(EXPLOSION_FRAMES)

def choose_spawn_pattern(obstacles, z_spawn):
    occupied_lanes = []
    for o in obstacles:
        if abs(o.z - z_spawn) < 0.15:
            occupied_lanes.append(o.lane)
            if o.kind == "roadblock":
                occupied_lanes.append(o.lane + 1)
    available_lanes = [l for l in range(LANES) if l not in occupied_lanes]
    if not available_lanes:
        return []
    if len(available_lanes) >= 2 and random.random() < 0.05:
        lane = random.choice(available_lanes[:-1])
        if (lane + 1) in available_lanes:
            return [(lane, "roadblock")]
    count = 2 if (len(available_lanes) > 1 and random.random() < 0.1) else 1
    chosen = random.sample(available_lanes, count)
    new_obs = []
    for l in chosen:
        kind = "cone" if random.random() < 0.2 else "car"
        new_obs.append((l, kind))
    return new_obs

def draw_boost_warp(surf, intensity, origin=None):
    if intensity <= 0:
        return
    w, h = surf.get_size()
    if origin is None:
        origin = (w // 2, h // 2)
    ox, oy = origin
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    n = int(10 + 22 * intensity)
    max_len = int(140 + 220 * intensity)
    base_alpha = int(18 + 55 * intensity)
    for _ in range(n):
        ang = random.uniform(-2.6, 2.6)
        start_r = random.uniform(70, 160)
        vx, vy = pygame.math.Vector2(1, 0).rotate_rad(ang)
        x0 = ox + int(start_r * 1.15 * vx)
        y0 = oy + int(start_r * 0.95 * vy)
        end_r = start_r + random.uniform(max_len * 0.45, max_len)
        x1 = ox + int(end_r * 1.20 * vx)
        y1 = oy + int(end_r * 1.00 * vy)
        x0 = clamp(x0, -80, w + 80); y0 = clamp(y0, -80, h + 80)
        x1 = clamp(x1, -80, w + 80); y1 = clamp(y1, -80, h + 80)
        thick = 1 if random.random() < 0.85 else 2
        dist = max(1, ((x0 - ox) ** 2 + (y0 - oy) ** 2) ** 0.5)
        fade = clamp(dist / 260.0, 0.25, 1.0)
        a = int(base_alpha * fade)
        col = (200, 255, 255, a)
        pygame.draw.line(overlay, col, (x0, y0), (x1, y1), thick)
    overlay.set_alpha(int(160 * intensity))
    surf.blit(overlay, (0, 0))

def draw_info_overlay(target_surf, info_alpha, started, alive, paused, counting_down, ammo, reloading):
    """No panel, no borders: just darken + text."""
    if info_alpha <= 1:
        return

    a = int(info_alpha)

    # darken whole screen
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, int(190 * (a / 255.0))))
    target_surf.blit(overlay, (0, 0))

    # text block (centered-ish)
    cx = W // 2
    top = H // 2 - 240

    draw_text_with_outline(target_surf, "CONTROLS", BIG_FONT, WHITE, (cx, top), center=True)
    y = top + 80

    reload_sec = RELOAD_TIME / 60.0

    lines = [
        ("Move left",  "LEFT / A"),
        ("Move right", "RIGHT / D"),
        ("Boost",      "UP / W"),
        ("Brake",      "DOWN / S"),
        ("Shoot",      "SPACE"),
        ("Pause",      "ESC"),
        ("Info",       "I"),
        ("Quit",       "Q"),
        ("Restart (crash)", "R"),
        ("", ""),
        ("Gameplay", ""),
        ("Enemy car HP", f"{CAR_MAX_HP} hits"),
        ("Magazine size", f"{MAG_SIZE} shots"),
        ("Reload time", f"{reload_sec:.1f}s"),
    ]

    # column positions
    lx = cx - 300
    rx = cx + 60

    key_font = pygame.font.SysFont("Arial", 22, bold=True)

    for left, right in lines:
        if left == "" and right == "":
            y += 16
            continue
        if right == "" and left != "":
            draw_text_with_outline(target_surf, left, key_font, NEON_CYAN, (lx, y))
            y += 34
            continue
        draw_text_with_outline(target_surf, left, FONT, WHITE, (lx, y))
        draw_text_with_outline(target_surf, right, key_font, WHITE, (rx, y))
        y += 30

    # dynamic status line
    status = []
    if not started:
        status.append("Menu")
    else:
        if counting_down:
            status.append("Countdown")
        elif not alive:
            status.append("Crashed")
        elif paused:
            status.append("Paused")
        else:
            status.append("Racing")

    if started and alive and (not counting_down):
        if reloading:
            status.append("Reloading…")
        else:
            status.append(f"Ammo {ammo}/{MAG_SIZE}")

    draw_text_with_outline(
        target_surf,
        " | ".join(status),
        SMALL_FONT,
        (200, 200, 200),
        (lx, H - 110)
    )
    draw_text_with_outline(
        target_surf,
        "Click anywhere or press ESC / I to close",
        SMALL_FONT,
        (200, 200, 200),
        (lx, H - 85)
    )

def draw_ammo_hud(frame, ammo, reloading):
    hud_x, hud_y = 20, 92

    if reloading:
        draw_text_with_outline(frame, "RELOADING...", FONT, NEON_RED, (hud_x, hud_y))
        hud_y += 28

    icon_h = 38
    icon_w = int(MAG_ICON.get_width() * (icon_h / max(1, MAG_ICON.get_height())))
    mag_icon_s = scale_cached(MAG_ICON, (icon_w, icon_h), SCALE_CACHE)
    frame.blit(mag_icon_s, (hud_x, hud_y))

    pip_x = hud_x + icon_w + 12
    pip_y = hud_y + 8
    pip_w, pip_h, pip_gap = 10, 20, 4
    total_w = MAG_SIZE * (pip_w + pip_gap) - pip_gap

    pygame.draw.rect(frame, (0, 0, 0), (pip_x - 6, pip_y - 6, total_w + 12, pip_h + 12), border_radius=6)

    for i in range(MAG_SIZE):
        x = pip_x + i * (pip_w + pip_gap)
        col = NEON_CYAN if i < ammo else (60, 60, 70)
        pygame.draw.rect(frame, col, (x, pip_y, pip_w, pip_h), border_radius=3)

# --- MAIN ---
def main():
    bullets = []
    explosions = []

    # screen shake
    shake_frames = 0
    shake_strength = 0

    def start_shake(frames, strength):
        nonlocal shake_frames, shake_strength
        shake_frames = max(shake_frames, frames)
        shake_strength = max(shake_strength, strength)

    player = None
    selected_car_idx = 0
    obstacles = []
    buildings = []
    score = 0
    last_score = 0
    alive = True
    paused = False
    started = False

    counting_down = False
    countdown_timer = 0
    countdown_stage = 3

    base_speed = 0.0015
    speed_ramp = 0.0000002
    speed = base_speed

    dash_offset = 0.0
    spawn_progress = 0.0
    building_spawn_progress = 0.0
    spawn_threshold = 0.45

    # shooting / ammo
    shoot_cooldown = 0
    ammo = MAG_SIZE
    reloading = False
    reload_timer = 0

    # --- INFO OVERLAY (fade + dynamic) ---
    show_info = False
    info_alpha = 0.0
    INFO_FADE_SPEED = 900.0

    def toggle_info(open_it=None):
        nonlocal show_info
        if open_it is None:
            show_info = not show_info
        else:
            show_info = bool(open_it)

    if os.path.exists(MUSIC_PATH):
        try:
            pygame.mixer.music.load(MUSIC_PATH)
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(-1)
        except:
            pass

    enemy_cycle_i = 0
    btn_w, btn_h = 200, 50
    center_x = W // 2 - btn_w // 2
    car_card_w, car_card_h = 100, 140
    car_spacing = 30
    total_cars_w = (len(PLAYER_MENU_VIEWS) * car_card_w) + ((len(PLAYER_MENU_VIEWS)-1) * car_spacing)
    start_x = W // 2 - total_cars_w // 2
    cards_y = H // 2 - 100

    car_rects = []
    for i in range(len(PLAYER_MENU_VIEWS)):
        r = pygame.Rect(start_x + i * (car_card_w + car_spacing), cards_y, car_card_w, car_card_h)
        car_rects.append(r)

    btn_play = pygame.Rect(center_x, H // 2 + 80, btn_w, btn_h)
    btn_quit_menu = pygame.Rect(center_x, H // 2 + 140, btn_w, btn_h)
    btn_restart = pygame.Rect(center_x, H // 2 + 40, btn_w, btn_h)
    btn_quit_over = pygame.Rect(center_x, H // 2 + 120, btn_w, btn_h)

    # info button top-right
    btn_info = pygame.Rect(W - 70, 20, 50, 50)

    while True:
        dt = clock.tick(60)
        dt_s = dt / 1000.0

        # fade update (always)
        target = 255.0 if show_info else 0.0
        if info_alpha < target:
            info_alpha = min(target, info_alpha + INFO_FADE_SPEED * dt_s)
        elif info_alpha > target:
            info_alpha = max(target, info_alpha - INFO_FADE_SPEED * dt_s)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                # if info overlay visible, clicking anywhere closes it (and doesn't click through)
                if info_alpha > 5:
                    toggle_info(False)
                    continue

                if btn_info.collidepoint(event.pos):
                    toggle_info()
                    continue

                if not started:
                    for i, r in enumerate(car_rects):
                        if r.collidepoint(event.pos):
                            selected_car_idx = i
                    if btn_play.collidepoint(event.pos):
                        started = True
                        counting_down = True
                        countdown_stage = 3
                        countdown_timer = 60
                        player = Player(PLAYER_DRIVE_SPRITES[selected_car_idx])
                        ammo = MAG_SIZE
                        reloading = False
                        reload_timer = 0
                        paused = False
                        alive = True
                        score = 0
                        last_score = 0
                        bullets.clear()
                        explosions.clear()
                        obstacles.clear()
                        buildings.clear()
                    if btn_quit_menu.collidepoint(event.pos):
                        pygame.quit()
                        sys.exit()
                elif not alive:
                    if btn_restart.collidepoint(event.pos):
                        return main()
                    if btn_quit_over.collidepoint(event.pos):
                        pygame.quit()
                        sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit()

                if event.key == pygame.K_i:
                    toggle_info()
                    continue

                if event.key == pygame.K_ESCAPE:
                    if info_alpha > 5 or show_info:
                        toggle_info(False)
                        continue
                    if started and alive and (not counting_down):
                        paused = not paused
                    continue

                if not started:
                    if event.key == pygame.K_LEFT:
                        selected_car_idx = max(0, selected_car_idx - 1)
                    if event.key == pygame.K_RIGHT:
                        selected_car_idx = min(len(PLAYER_MENU_VIEWS)-1, selected_car_idx + 1)
                    if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        started = True
                        counting_down = True
                        countdown_stage = 3
                        countdown_timer = 60
                        player = Player(PLAYER_DRIVE_SPRITES[selected_car_idx])
                        ammo = MAG_SIZE
                        reloading = False
                        reload_timer = 0
                        paused = False
                        alive = True
                        score = 0
                        last_score = 0
                        bullets.clear()
                        explosions.clear()
                        obstacles.clear()
                        buildings.clear()

                elif alive and not counting_down:
                    if not paused:
                        if event.key in (pygame.K_LEFT, pygame.K_a):
                            player.move_left()
                        if event.key in (pygame.K_RIGHT, pygame.K_d):
                            player.move_right()

                        if event.key == pygame.K_SPACE:
                            if (not reloading) and ammo > 0 and shoot_cooldown <= 0:
                                bullets.append(Bullet(player.lane, player.z - 0.08))
                                shoot_cooldown = 10
                                ammo -= 1
                                if ammo <= 0:
                                    reloading = True
                                    reload_timer = RELOAD_TIME

                else:
                    if event.key == pygame.K_r:
                        return main()

        keys = pygame.key.get_pressed()

        # update shake
        cam_dx = cam_dy = 0
        if shake_frames > 0:
            cam_dx = random.randint(-shake_strength, shake_strength)
            cam_dy = random.randint(-shake_strength, shake_strength)
            shake_frames -= 1
            if shake_frames <= 0:
                shake_strength = 0

        if shoot_cooldown > 0:
            shoot_cooldown -= 1

        # reload update
        if started and alive and (not paused) and (not counting_down):
            if reloading:
                reload_timer -= 1
                if reload_timer <= 0:
                    reloading = False
                    ammo = MAG_SIZE

        if started and alive and not paused:
            if counting_down:
                countdown_timer -= 1
                if countdown_timer <= 0:
                    countdown_stage -= 1
                    countdown_timer = 60
                    if countdown_stage < 0:
                        counting_down = False
            else:
                boosting = keys[pygame.K_UP] or keys[pygame.K_w]
                braking = keys[pygame.K_DOWN] or keys[pygame.K_s]
                target_speed = base_speed * 1.5 if boosting else (base_speed * 0.7 if braking else base_speed)
                speed = lerp(speed, target_speed, 0.1)

                if SOUND_ENGINE:
                    if boosting and alive:
                        if SOUND_ENGINE.get_num_channels() == 0:
                            SOUND_ENGINE.play(-1)
                    else:
                        SOUND_ENGINE.stop()

                player.update(boosting)
                score += 1 + int(speed * 1000)
                base_speed += speed_ramp * dt

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

                building_spawn_progress += speed
                if building_spawn_progress > 0.12:
                    building_spawn_progress = 0
                    min_gap = 0.2
                    left_occupied = any(b.side == -1 and abs(b.z - Z_SPAWN_MIN) < min_gap for b in buildings)
                    if not left_occupied and random.random() < 0.7:
                        buildings.append(Building(-1, Z_SPAWN_MIN))
                    right_occupied = any(b.side == 1 and abs(b.z - Z_SPAWN_MIN) < min_gap for b in buildings)
                    if not right_occupied and random.random() < 0.7:
                        buildings.append(Building(1, Z_SPAWN_MIN))

                p_rect = player.get_rect()

                for b in buildings[:]:
                    b.update(speed)
                    if b.z > 1.3:
                        buildings.remove(b)

                for obs in obstacles[:]:
                    obs.update(speed)
                    if obs.z > 1.3:
                        obstacles.remove(obs)
                        continue
                    if 0.85 < obs.z < 1.0:
                        o_rect = obs.get_rect()
                        hitbox = o_rect.inflate(-15, -15)
                        if p_rect.colliderect(hitbox):
                            alive = False
                            last_score = score
                            if SOUND_ENGINE:
                                SOUND_ENGINE.stop()
                            explosions.append(Explosion(p_rect.centerx, p_rect.centery, player.z))
                            start_shake(22, 10)

                for blt in bullets[:]:
                    blt.update()
                    if blt.z < 0.02:
                        bullets.remove(blt)

                for blt in bullets[:]:
                    brect = blt.get_rect()
                    hit_any = False
                    for obs in obstacles[:]:
                        orect = obs.get_rect()
                        if not brect.colliderect(orect):
                            continue
                        hit_any = True
                        if obs.kind == "car":
                            obs.hp -= 1
                            score += 40
                            if obs.hp <= 0:
                                explosions.append(Explosion(orect.centerx, orect.centery, obs.z))
                                start_shake(12, 7)
                                obstacles.remove(obs)
                                score += 300
                        else:
                            explosions.append(Explosion(orect.centerx, orect.centery, obs.z))
                            start_shake(8, 5)
                            obstacles.remove(obs)
                            score += 100
                        break
                    if hit_any and blt in bullets:
                        bullets.remove(blt)

                for ex in explosions[:]:
                    ex.update()
                    if ex.done():
                        explosions.remove(ex)

                dash_offset = (dash_offset + speed * 2.0) % 1.0
        else:
            for ex in explosions[:]:
                ex.update()
                if ex.done():
                    explosions.remove(ex)

        # --- RENDER ---
        if not started:
            if IMG_POSTER:
                screen.blit(IMG_POSTER, (0, 0))
            else:
                screen.fill((0, 0, 0))

            for i, menu_img in enumerate(PLAYER_MENU_VIEWS):
                rect = car_rects[i]
                s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                pygame.draw.rect(s, (16, 24, 48, 230), s.get_rect(), border_radius=10)
                screen.blit(s, rect.topleft)
                g = pygame.Surface((rect.width, rect.height // 2), pygame.SRCALPHA)
                pygame.draw.rect(g, (255, 255, 255, 15), g.get_rect(), border_top_left_radius=10, border_top_right_radius=10)
                screen.blit(g, rect.topleft)

                iw, ih = menu_img.get_size()
                aspect = iw / ih
                target_w = rect.width - 20
                target_h = int(target_w / aspect)
                if target_h > rect.height - 40:
                    target_h = rect.height - 40
                    target_w = int(target_h * aspect)
                menu_car_img = pygame.transform.smoothscale(menu_img, (target_w, target_h))
                img_rect = menu_car_img.get_rect(center=rect.center)

                if i == selected_car_idx:
                    glow_rect = rect.inflate(10, 10)
                    pygame.draw.rect(screen, NEON_CYAN, glow_rect, 3, border_radius=12)
                    s_glow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                    pygame.draw.rect(s_glow, (0, 255, 255, 30), s_glow.get_rect(), border_radius=10)
                    screen.blit(s_glow, rect.topleft)
                else:
                    pygame.draw.rect(screen, (60, 70, 90), rect, 2, border_radius=10)

                screen.blit(menu_car_img, img_rect.topleft)

            draw_button(screen, btn_play, "PLAY")
            draw_button(screen, btn_quit_menu, "QUIT", is_danger=True)

            draw_button(screen, btn_info, "i" if info_alpha < 5 else "X", is_danger=(info_alpha >= 5))
            draw_info_overlay(screen, info_alpha, started, alive, paused, counting_down, ammo, reloading)

            pygame.display.flip()
            continue

        frame = pygame.Surface((W, H))
        draw_background_and_terrain(frame, dash_offset)
        buildings.sort(key=lambda b: b.z)
        for b in buildings:
            b.draw(frame)

        draw_road(frame, dash_offset)

        obstacles.sort(key=lambda o: -o.z)
        for obs in obstacles:
            obs.draw(frame)

        for blt in bullets:
            blt.draw(frame)

        if player:
            player.draw(frame)

        for ex in explosions:
            ex.draw(frame)

        draw_text_with_outline(frame, f"SCORE: {score}", FONT, WHITE, (20, 20))
        speed_pct = min(1.0, (speed / 0.01))
        pygame.draw.rect(frame, (50, 50, 50), (20, 60, 200, 20), border_radius=5)
        pygame.draw.rect(frame, NEON_CYAN, (20, 60, int(200 * speed_pct), 20), border_radius=5)
        draw_text_with_outline(frame, "SPEED", SMALL_FONT, WHITE, (25, 62))

        if started:
            draw_ammo_hud(frame, ammo, reloading)

        if counting_down:
            draw_countdown_lights(frame, countdown_stage)

        if not alive:
            s = pygame.Surface((W, H), pygame.SRCALPHA)
            s.fill((50, 0, 0, 200))
            frame.blit(s, (0, 0))
            txt = BIG_FONT.render("CRASHED!", True, (255, 50, 50))
            frame.blit(txt, (W//2 - txt.get_width()//2, H//2 - 120))
            score_txt = FONT.render(f"YOUR SCORE: {last_score}", True, WHITE)
            frame.blit(score_txt, (W//2 - score_txt.get_width()//2, H//2 - 30))
            draw_button(frame, btn_restart, "RESTART")
            draw_button(frame, btn_quit_over, "QUIT", is_danger=True)

        elif paused:
            s = pygame.Surface((W, H), pygame.SRCALPHA)
            s.fill((0, 0, 0, 150))
            frame.blit(s, (0, 0))
            txt = BIG_FONT.render("PAUZE", True, WHITE)
            frame.blit(txt, (W//2 - txt.get_width()//2, H//2))

        draw_button(frame, btn_info, "i" if info_alpha < 5 else "X", is_danger=(info_alpha >= 5))
        draw_info_overlay(frame, info_alpha, started, alive, paused, counting_down, ammo, reloading)

        # --- BOOST EFFECT (ONLY while accelerating) ---
        car_origin = None
        if player:
            pr = player.get_rect()
            car_origin = (pr.centerx, pr.centery - int(pr.h * 0.25))

        boosting_now = False
        if started and alive and (not paused) and (not counting_down) and (info_alpha <= 5):
            boosting_now = (keys[pygame.K_UP] or keys[pygame.K_w])

        final_frame = frame

        if boosting_now:
            speed_pct = min(1.0, (speed / 0.01))
            boost_intensity = clamp(speed_pct, 0.0, 1.0)

            ghost = frame.copy()
            ghost.blit(frame, (0, 6))
            ghost.set_alpha(int(60 + 90 * boost_intensity))
            frame.blit(ghost, (0, 0))

            if car_origin:
                draw_boost_warp(frame, boost_intensity, origin=car_origin)

            zoom = 1.0 + (0.06 * boost_intensity)
            zoom_w = int(W * zoom)
            zoom_h = int(H * zoom)
            zoomed = pygame.transform.smoothscale(frame, (zoom_w, zoom_h))
            crop_x = (zoom_w - W) // 2
            crop_y = (zoom_h - H) // 2
            final_frame = zoomed.subsurface((crop_x, crop_y, W, H))

        screen.fill((0, 0, 0))
        screen.blit(final_frame, (cam_dx, cam_dy))
        pygame.display.flip()

if __name__ == "__main__":
    main()
