# runner_25d_cars.py
# 2.5D fake-3D lane runner (cars) — single-file pygame game
#
# Controls:
#   Left/Right (or A/D): change lane (in-game)
#   Up/W: boost (faster)
#   Down/S: brake (slower)
#   Esc: pause/resume (in-game)
#   Q: quit
#
# Clickable menus:
#   Main menu: Play / Quit
#   Pause menu: Resume / Restart / Quit
#   Crash screen: Restart / Main Menu / Quit
#
# Assets folder:
#   assets/race-car.png (player)
#   assets/car.png (fallback enemy)
#   Optional multiple enemy cars:
#     assets/enemy_car_1.png, enemy_car_2.png, ...

import pygame
import random
import sys
import math
import os

# ----------------------------
# Asset helpers
# ----------------------------
ASSETS = os.path.join(os.path.dirname(__file__), "assets")

def load_image(name: str) -> pygame.Surface:
    path = os.path.join(ASSETS, name)
    return pygame.image.load(path).convert_alpha()

def scale_cached(img: pygame.Surface, size: tuple[int, int], cache: dict) -> pygame.Surface:
    key = (id(img), size[0], size[1])
    if key not in cache:
        cache[key] = pygame.transform.smoothscale(img, size)
    return cache[key]

# Fake perspective warp (only for obstacle cars)
WARP_CACHE = {}

def perspective_warp(img: pygame.Surface, top_scale=0.82, bottom_scale=1.00, slices=18) -> pygame.Surface:
    w, h = img.get_size()
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    for i in range(slices):
        y0 = int(h * i / slices)
        y1 = int(h * (i + 1) / slices)
        band_h = max(1, y1 - y0)

        t = i / (slices - 1) if slices > 1 else 1.0
        s = top_scale + (bottom_scale - top_scale) * t
        band_w = max(1, int(w * s))

        band = img.subsurface((0, y0, w, band_h))
        band_scaled = pygame.transform.smoothscale(band, (band_w, band_h))

        x = (w - band_w) // 2
        out.blit(band_scaled, (x, y0))
    return out

def warp_cached(img: pygame.Surface, size: tuple[int, int], top_scale: float, bottom_scale: float) -> pygame.Surface:
    key = (id(img), size[0], size[1], round(top_scale, 3), round(bottom_scale, 3))
    if key not in WARP_CACHE:
        scaled = pygame.transform.smoothscale(img, size)
        WARP_CACHE[key] = perspective_warp(scaled, top_scale=top_scale, bottom_scale=bottom_scale, slices=18)
    return WARP_CACHE[key]

# ----------------------------
# Pygame init
# ----------------------------
pygame.init()

W, H = 900, 700
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Highway Escape (2.5D) - Pygame")
clock = pygame.time.Clock()
FONT = pygame.font.SysFont(None, 28)
BIG = pygame.font.SysFont(None, 56)

SCALE_CACHE = {}

# ----------------------------
# Load sprites
# ----------------------------
ROTATE_DEG = 90  # change to -90 or 180 if your sprites face the wrong way

IMG_PLAYER = pygame.transform.rotate(load_image("race-car.png"), ROTATE_DEG)

# Optional multiple enemy cars (cycle through them)
ENEMY_CAR_FILES = [
    "enemy_car_1.png",
    "enemy_car_2.png",
    "enemy_car_3.png",
    "enemy_car_4.png",
]
IMG_ENEMIES = []
for fn in ENEMY_CAR_FILES:
    path = os.path.join(ASSETS, fn)
    if os.path.exists(path):
        IMG_ENEMIES.append(pygame.transform.rotate(load_image(fn), ROTATE_DEG))

# Fallback to single car.png if no enemy_car_* exist
if not IMG_ENEMIES:
    IMG_ENEMIES = [pygame.transform.rotate(load_image("car.png"), ROTATE_DEG)]

# Only warp obstacle cars (player stays crisp)
USE_OBSTACLE_WARP = True
OBSTACLE_WARP_TOP = 0.78
OBSTACLE_WARP_BOTTOM = 1.00

# ----------------------------
# World settings
# ----------------------------
LANES = 3

ROAD_NEAR_Y = H - 40
ROAD_FAR_Y = 120
ROAD_NEAR_W = int(W * 0.85)
ROAD_FAR_W = int(W * 0.22)
ROAD_CENTER_X = W // 2

Z_SPAWN_MIN = 0.03
Z_SPAWN_MAX = 0.20

def clamp(x, a, b):
    return max(a, min(b, x))

def lerp(a, b, t):
    return a + (b - a) * t

def ease_in(t):
    return t * t

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

def road_lane_width_at_y(y):
    left, right = road_edges_at_y(y)
    return (right - left) / LANES

def draw_background_and_terrain(surf, t_scroll):
    # Sky gradient
    for y in range(H):
        k = y / H
        col = (int(12 + 30 * (1 - k)), int(18 + 45 * (1 - k)), int(28 + 70 * (1 - k)))
        pygame.draw.line(surf, col, (0, y), (W, y))

    # Hills
    hill_y = ROAD_FAR_Y + 10
    pts = []
    for x in range(0, W + 1, 40):
        yy = hill_y + int(20 * math.sin((x * 0.01) + 2.0)) + int(10 * math.sin((x * 0.02) + 0.5))
        pts.append((x, yy))
    pts += [(W, H), (0, H)]
    pygame.draw.polygon(surf, (20, 30, 25), pts)

    # Grass bands
    bands = 60
    for i in range(bands):
        t0 = i / bands
        t1 = (i + 1) / bands

        y0 = lerp(ROAD_FAR_Y, ROAD_NEAR_Y, t0)
        y1 = lerp(ROAD_FAR_Y, ROAD_NEAR_Y, t1)

        left0, right0 = road_edges_at_y(y0)
        left1, right1 = road_edges_at_y(y1)

        stripe = int(((t0 + t_scroll) * 20) % 2)
        base = 28 + stripe * 6
        grass_col = (base, base + 18, base)

        left_poly = [(0, y0), (left0, y0), (left1, y1), (0, y1)]
        right_poly = [(right0, y0), (W, y0), (W, y1), (right1, y1)]
        pygame.draw.polygon(surf, grass_col, left_poly)
        pygame.draw.polygon(surf, grass_col, right_poly)

def draw_road(surf, dash_offset=0.0):
    far_left = ROAD_CENTER_X - ROAD_FAR_W // 2
    far_right = ROAD_CENTER_X + ROAD_FAR_W // 2
    near_left = ROAD_CENTER_X - ROAD_NEAR_W // 2
    near_right = ROAD_CENTER_X + ROAD_NEAR_W // 2

    road_poly = [(far_left, ROAD_FAR_Y), (far_right, ROAD_FAR_Y), (near_right, ROAD_NEAR_Y), (near_left, ROAD_NEAR_Y)]
    pygame.draw.polygon(surf, (40, 40, 46), road_poly)
    pygame.draw.lines(surf, (95, 95, 105), True, road_poly, 3)

    for i in range(1, LANES):
        far_lane_w = ROAD_FAR_W / LANES
        near_lane_w = ROAD_NEAR_W / LANES
        x_far = (ROAD_CENTER_X - ROAD_FAR_W / 2) + far_lane_w * i
        x_near = (ROAD_CENTER_X - ROAD_NEAR_W / 2) + near_lane_w * i
        pygame.draw.line(surf, (75, 75, 84), (x_far, ROAD_FAR_Y), (x_near, ROAD_NEAR_Y), 2)

    dash_count = 18
    for k in range(dash_count):
        t0 = ((k / dash_count) + dash_offset) % 1.0
        t1 = ((k + 0.45) / dash_count + dash_offset) % 1.0
        y0 = lerp(ROAD_FAR_Y, ROAD_NEAR_Y, t0)
        y1 = lerp(ROAD_FAR_Y, ROAD_NEAR_Y, t1)
        alpha = int(lerp(40, 190, t0))
        pygame.draw.line(surf, (alpha, alpha, alpha), (ROAD_CENTER_X, y0), (ROAD_CENTER_X, y1), 3)

# ----------------------------
# UI Button
# ----------------------------
class Button:
    def __init__(self, rect, text, font, action):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.action = action
        self.hover = False
        self.down = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.down = True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_down = self.down
            self.down = False
            if was_down and self.rect.collidepoint(event.pos):
                return self.action
        return None

    def draw(self, surf):
        shadow = self.rect.move(0, 4)
        pygame.draw.rect(surf, (0, 0, 0), shadow, border_radius=16)

        bg = (38, 38, 44)
        if self.hover:
            bg = (52, 52, 60)
        if self.down:
            bg = (30, 30, 36)

        pygame.draw.rect(surf, bg, self.rect, border_radius=16)
        pygame.draw.rect(surf, (120, 120, 140), self.rect, width=2, border_radius=16)

        label = self.font.render(self.text, True, (245, 245, 248))
        surf.blit(label, label.get_rect(center=self.rect.center))

def draw_overlay(frame, title_text, buttons):
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    frame.blit(overlay, (0, 0))

    title = BIG.render(title_text, True, (255, 255, 255))
    frame.blit(title, (W // 2 - title.get_width() // 2, H // 2 - 170))

    for b in buttons:
        b.draw(frame)

# ----------------------------
# Game objects
# ----------------------------
class Player:
    def __init__(self):
        self.lane = 1
        self.target_lane = 1
        self.lane_blend = 1.0
        self.lane_change_speed = 0.22

        self.z = 0.92
        self.base_w = 72
        self.base_h = 100

        self.invuln_timer = 0

    def move_left(self):
        self.target_lane = max(0, self.target_lane - 1)

    def move_right(self):
        self.target_lane = min(LANES - 1, self.target_lane + 1)

    def update(self):
        if self.invuln_timer > 0:
            self.invuln_timer -= 1

        if self.lane != self.target_lane:
            self.lane_blend += self.lane_change_speed
            if self.lane_blend >= 1.0:
                self.lane = self.target_lane
                self.lane_blend = 1.0
        else:
            self.lane_blend = 1.0

    def screen_rect(self):
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

    def draw(self, surf, sprite):
        r = self.screen_rect()
        img = scale_cached(sprite, (r.w, r.h), SCALE_CACHE)  # player stays unwarped
        surf.blit(img, r.topleft)

class Obstacle:
    def __init__(self, lane, z, kind="car", sprite=None):
        self.lane = lane
        self.z = z
        self.kind = kind
        self.sprite = sprite
        self.scored_nearmiss = False

        if kind == "car":
            self.base_w, self.base_h = 75, 145
        elif kind == "cone":
            self.base_w, self.base_h = 34, 34
        elif kind == "roadblock":
            self.base_w, self.base_h = 150, 65
        else:
            self.base_w, self.base_h = 70, 70

    def update(self, dz):
        self.z += dz

    def screen_rect(self):
        y = y_from_z(self.z)
        x = lane_center_x_at_y(self.lane, y)

        scale = lerp(0.22, 1.18, self.z)
        w = int(self.base_w * scale)
        h = int(self.base_h * scale)

        rect = pygame.Rect(0, 0, w, h)
        rect.center = (int(x), int(y - h * 0.10))
        return rect

    def draw(self, surf):
        r = self.screen_rect()

        if self.kind == "car":
            car_img = self.sprite if self.sprite is not None else IMG_ENEMIES[0]
            if USE_OBSTACLE_WARP:
                img = warp_cached(car_img, (r.w, r.h), OBSTACLE_WARP_TOP, OBSTACLE_WARP_BOTTOM)
            else:
                img = scale_cached(car_img, (r.w, r.h), SCALE_CACHE)
            surf.blit(img, r.topleft)

        elif self.kind == "cone":
            pygame.draw.rect(surf, (255, 180, 60), r, border_radius=6)
            stripe = pygame.Rect(r.x, r.y + r.h * 0.45, r.w, r.h * 0.18)
            pygame.draw.rect(surf, (255, 240, 220), stripe, border_radius=4)

        elif self.kind == "roadblock":
            pygame.draw.rect(surf, (235, 235, 80), r, border_radius=10)
            for i in range(5):
                x0 = r.x + int((i / 5) * r.w)
                pygame.draw.line(surf, (60, 60, 60), (x0, r.bottom), (x0 + 18, r.y), 4)

        else:
            pygame.draw.rect(surf, (220, 220, 220), r, border_radius=8)

def roadblock_rect_for_lane(left_lane, z):
    y = y_from_z(z)
    x0 = lane_center_x_at_y(left_lane, y)
    x1 = lane_center_x_at_y(left_lane + 1, y)
    x = (x0 + x1) * 0.5

    lane_w = road_lane_width_at_y(y)
    base_w = lane_w * 2 * 0.95
    base_h = 65
    scale = lerp(0.22, 1.18, z)

    w = int(base_w * scale)
    h = int(base_h * scale)

    rect = pygame.Rect(0, 0, w, h)
    rect.center = (int(x), int(y - h * 0.10))
    return rect

# ----------------------------
# Fair spawner
# ----------------------------
def choose_spawn_pattern(obstacles, z_spawn):
    # Consider only "soon" obstacles as blocking
    DANGER_Z = 0.65

    # Spacing: strict same-lane, looser adjacent lanes (prevents middle-lane bias)
    MIN_SAME_LANE_GAP_Z = 0.48
    MIN_ADJ_LANE_GAP_Z  = 0.30

    TWO_OBS_CHANCE = 0.22
    CONE_CHANCE = 0.15

    occupied = set()
    for o in obstacles:
        if o.z >= DANGER_Z:
            if o.kind == "roadblock":
                occupied.add(o.lane)
                occupied.add(o.lane + 1)
            else:
                occupied.add(o.lane)

    def lane_has_space(lane):
        for o in obstacles:
            if o.kind == "roadblock":
                occ_lanes = {o.lane, o.lane + 1}
            else:
                occ_lanes = {o.lane}

            for occ in occ_lanes:
                dz = abs(o.z - z_spawn)
                if occ == lane:
                    if dz < MIN_SAME_LANE_GAP_Z:
                        return False
                elif abs(occ - lane) == 1:
                    if dz < MIN_ADJ_LANE_GAP_Z:
                        return False
        return True

    free_lanes = [l for l in range(LANES) if l not in occupied and lane_has_space(l)]
    if not free_lanes:
        return []

    # Never block all lanes
    max_blockable = LANES - 1
    remaining_open_needed = 1
    block_budget = max_blockable - len(occupied)
    block_budget = max(0, min(block_budget, max_blockable))

    # Allow roadblocks only if they still leave an escape lane
    roadblock_allowed = False
    roadblock_lane = 0
    if block_budget >= 2:
        candidates = []
        for left_lane in (0, 1):
            blocks = {left_lane, left_lane + 1}
            if len(blocks.union(occupied)) <= LANES - remaining_open_needed:
                if lane_has_space(left_lane) and lane_has_space(left_lane + 1):
                    candidates.append(left_lane)
        if candidates:
            roadblock_allowed = True
            roadblock_lane = random.choice(candidates)

    if roadblock_allowed and random.random() < 0.10:
        return [(roadblock_lane, "roadblock")]

    count = 1
    if block_budget >= 1 and random.random() < TWO_OBS_CHANCE and len(free_lanes) >= 2:
        count = 2

    lanes = free_lanes[:]
    random.shuffle(lanes)

    out = []
    for i in range(min(count, len(lanes))):
        kind = "cone" if random.random() < CONE_CHANCE else "car"
        out.append((lanes[i], kind))
    return out

# ----------------------------
# Main
# ----------------------------
def main():
    # State machine: "menu", "game", "pause", "dead"
    state = "menu"

    def reset_game():
        nonlocal player, obstacles, score, distance, alive, base_speed, speed, dash_offset
        nonlocal spawn_progress, next_spawn_gap, shake_timer, shake_mag, enemy_cycle_i
        player = Player()
        obstacles = []
        score = 0
        distance = 0.0
        alive = True

        base_speed = 0.003
        speed = base_speed
        dash_offset = 0.0

        spawn_progress = 0.0
        next_spawn_gap = random.uniform(0.18, 0.32)

        shake_timer = 0
        shake_mag = 0

        enemy_cycle_i = 0

    # init game data once
    player = Player()
    obstacles = []
    score = 0
    distance = 0.0
    alive = True

    base_speed = 0.003
    speed = base_speed
    speed_ramp = 0.0000002
    dash_offset = 0.0

    spawn_progress = 0.0
    next_spawn_gap = random.uniform(0.18, 0.32)

    shake_timer = 0
    shake_mag = 0

    enemy_cycle_i = 0

    # Buttons
    menu_buttons = [
        Button((W // 2 - 170, H // 2 - 40, 340, 64), "Play", BIG, "play"),
        Button((W // 2 - 170, H // 2 + 45, 340, 64), "Quit", BIG, "quit"),
    ]

    pause_buttons = [
        Button((W // 2 - 170, H // 2 - 90, 340, 64), "Resume", BIG, "resume"),
        Button((W // 2 - 170, H // 2 - 5, 340, 64), "Restart", BIG, "restart"),
        Button((W // 2 - 170, H // 2 + 80, 340, 64), "Quit", BIG, "quit"),
    ]

    dead_buttons = [
        Button((W // 2 - 170, H // 2 - 90, 340, 64), "Restart", BIG, "restart"),
        Button((W // 2 - 170, H // 2 - 5, 340, 64), "Main Menu", BIG, "menu"),
        Button((W // 2 - 170, H // 2 + 80, 340, 64), "Quit", BIG, "quit"),
    ]

    while True:
        dt = clock.tick(60)

        # ----------------------------
        # Input
        # ----------------------------
        boosting = False
        braking = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # global hotkeys
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit()

                if event.key == pygame.K_ESCAPE:
                    if state == "game":
                        state = "pause"
                    elif state == "pause":
                        state = "game"

                if event.key == pygame.K_r:
                    if state in ("pause", "dead"):
                        reset_game()
                        state = "game"

            # clickable UI
            if state == "menu":
                for b in menu_buttons:
                    action = b.handle_event(event)
                    if action == "play":
                        reset_game()
                        state = "game"
                    elif action == "quit":
                        pygame.quit()
                        sys.exit()

            elif state == "pause":
                for b in pause_buttons:
                    action = b.handle_event(event)
                    if action == "resume":
                        state = "game"
                    elif action == "restart":
                        reset_game()
                        state = "game"
                    elif action == "quit":
                        pygame.quit()
                        sys.exit()

            elif state == "dead":
                for b in dead_buttons:
                    action = b.handle_event(event)
                    if action == "restart":
                        reset_game()
                        state = "game"
                    elif action == "menu":
                        state = "menu"
                    elif action == "quit":
                        pygame.quit()
                        sys.exit()

            # in-game key controls only when actively playing
            if state == "game" and alive and event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    player.move_left()
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    player.move_right()

        keys = pygame.key.get_pressed()
        if state == "game" and alive:
            boosting = keys[pygame.K_UP] or keys[pygame.K_w]
            braking = keys[pygame.K_DOWN] or keys[pygame.K_s]

        # ----------------------------
        # Update (only in game)
        # ----------------------------
        if state == "game" and alive:
            player.update()

            base_speed += speed_ramp * dt
            if boosting:
                speed = base_speed * 1.45
            elif braking:
                speed = base_speed * 0.70
            else:
                speed = base_speed

            distance += speed * 1000.0
            score += 1 + int(speed * 20)

            spawn_progress += speed
            if spawn_progress >= next_spawn_gap:
                z0 = random.uniform(Z_SPAWN_MIN, Z_SPAWN_MAX)
                pattern = choose_spawn_pattern(obstacles, z0)

                for lane, kind in pattern:
                    if kind == "car":
                        sprite = IMG_ENEMIES[enemy_cycle_i]
                        enemy_cycle_i = (enemy_cycle_i + 1) % len(IMG_ENEMIES)
                        obstacles.append(Obstacle(lane, z0, kind=kind, sprite=sprite))
                    else:
                        obstacles.append(Obstacle(lane, z0, kind=kind))

                spawn_progress = 0.0
                next_spawn_gap = random.uniform(0.18, 0.32)

            for obs in obstacles:
                obs.update(speed)

            # despawn shortly after passing player
            obstacles = [o for o in obstacles if o.z < 0.96]

            p_rect = player.screen_rect()
            for obs in obstacles:
                o_rect = roadblock_rect_for_lane(obs.lane, obs.z) if obs.kind == "roadblock" else obs.screen_rect()

                if obs.kind in ("car", "cone") and obs.z > 0.93 and not obs.scored_nearmiss:
                    dx = abs(o_rect.centerx - p_rect.centerx)
                    thresh = max(18, int(p_rect.w * 0.22))
                    if dx < thresh and not p_rect.colliderect(o_rect):
                        score += 150
                        obs.scored_nearmiss = True
                        player.invuln_timer = 8

                if obs.z > 0.72 and p_rect.colliderect(o_rect):
                    alive = False
                    state = "dead"
                    shake_timer = 18
                    shake_mag = 10
                    break

            dash_offset = (dash_offset + speed * 2.2) % 1.0

        # ----------------------------
        # Draw
        # ----------------------------
        ox = oy = 0
        if shake_timer > 0:
            shake_timer -= 1
            angle = random.random() * math.tau
            mag = shake_mag * (shake_timer / 18.0)
            ox = int(math.cos(angle) * mag)
            oy = int(math.sin(angle) * mag)

        frame = pygame.Surface((W, H))
        draw_background_and_terrain(frame, t_scroll=dash_offset)
        draw_road(frame, dash_offset=dash_offset)

        # obstacles far->near
        for obs in sorted(obstacles, key=lambda o: o.z):
            if obs.kind == "roadblock":
                r = roadblock_rect_for_lane(obs.lane, obs.z)
                pygame.draw.rect(frame, (235, 235, 80), r, border_radius=10)
                for i in range(6):
                    x0 = r.x + int((i / 6) * r.w)
                    pygame.draw.line(frame, (60, 60, 60), (x0, r.bottom), (x0 + 18, r.y), 4)
            else:
                obs.draw(frame)

        # player always drawn (even on menu/pause for vibe)
        player.draw(frame, IMG_PLAYER)

        # HUD
        ui1 = FONT.render(f"Score: {score}", True, (240, 240, 245))
        ui2 = FONT.render(f"Speed: {base_speed:.3f}", True, (210, 210, 220))
        ui3 = FONT.render("Left/Right: lanes  |  Up: boost  |  Down: brake  |  Esc: menu", True, (180, 180, 190))
        frame.blit(ui1, (14, 10))
        frame.blit(ui2, (14, 36))
        frame.blit(ui3, (14, 62))

        # Menus
        if state == "menu":
            draw_overlay(frame, "HIGHWAY ESCAPE", menu_buttons)
            hint = FONT.render("Mouse: click buttons   |   Q: quit", True, (210, 210, 220))
            frame.blit(hint, (W // 2 - hint.get_width() // 2, H // 2 + 140))

        elif state == "pause":
            draw_overlay(frame, "PAUSED", pause_buttons)
            hint = FONT.render("Esc: resume   |   Q: quit", True, (210, 210, 220))
            frame.blit(hint, (W // 2 - hint.get_width() // 2, H // 2 + 160))

        elif state == "dead":
            draw_overlay(frame, "CRASH!", dead_buttons)
            hint = FONT.render("R: restart   |   Q: quit", True, (210, 210, 220))
            frame.blit(hint, (W // 2 - hint.get_width() // 2, H // 2 + 160))

        screen.fill((0, 0, 0))
        screen.blit(frame, (ox, oy))
        pygame.display.flip()

if __name__ == "__main__":
    main()
