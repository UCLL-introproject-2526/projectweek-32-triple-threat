import pygame
import random
import sys

pygame.init()

W, H = 900, 700
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("2.5D Endless Runner (Fake 3D) - Pygame Example")
clock = pygame.time.Clock()
FONT = pygame.font.SysFont(None, 32)

LANES = 3

# Road geometry (trapezoid)
ROAD_NEAR_Y = H - 40
ROAD_FAR_Y  = 120
ROAD_NEAR_W = int(W * 0.85)
ROAD_FAR_W  = int(W * 0.20)
ROAD_CENTER_X = W // 2

# Depth range: z=0 at far, z=1 near player
Z_SPAWN_MIN = 0.05
Z_SPAWN_MAX = 0.25

def clamp(x, a, b):
    return max(a, min(b, x))

def lerp(a, b, t):
    return a + (b - a) * t

def ease_in(t):  # makes movement feel more "3D"
    return t * t

def road_edges_at_y(y):
    """Return left_x, right_x for the road at screen y (linear interpolation)."""
    t = (y - ROAD_FAR_Y) / (ROAD_NEAR_Y - ROAD_FAR_Y)
    t = clamp(t, 0.0, 1.0)
    half_w = lerp(ROAD_FAR_W / 2, ROAD_NEAR_W / 2, t)
    return ROAD_CENTER_X - half_w, ROAD_CENTER_X + half_w

def y_from_z(z):
    """
    Map depth z in [0..1] to screen y in [ROAD_FAR_Y..ROAD_NEAR_Y].
    Use easing so things accelerate visually as they approach.
    """
    z = clamp(z, 0.0, 1.0)
    t = ease_in(z)
    return lerp(ROAD_FAR_Y, ROAD_NEAR_Y, t)

def lane_center_x_at_y(lane_idx, y):
    """Lane center x based on road width at y."""
    left, right = road_edges_at_y(y)
    lane_w = (right - left) / LANES
    return left + lane_w * (lane_idx + 0.5)

class Player:
    def __init__(self):
        self.lane = 1
        self.target_lane = 1
        self.lane_blend = 1.0  # 0..1 animation progress for lane change
        self.lane_change_speed = 0.18

        # near position
        self.z = 0.92  # close to camera
        self.base_w = 60
        self.base_h = 90

    def move_left(self):
        self.target_lane = max(0, self.target_lane - 1)

    def move_right(self):
        self.target_lane = min(LANES - 1, self.target_lane + 1)

    def update(self):
        if self.lane != self.target_lane:
            # animate lane change
            self.lane_blend += self.lane_change_speed
            if self.lane_blend >= 1.0:
                self.lane = self.target_lane
                self.lane_blend = 1.0
        else:
            self.lane_blend = 1.0

    def screen_rect(self):
        y = y_from_z(self.z)

        # if mid-lane-change: interpolate lane center between old and target
        if self.lane != self.target_lane:
            y_mid = y
            x_from = lane_center_x_at_y(self.lane, y_mid)
            x_to   = lane_center_x_at_y(self.target_lane, y_mid)
            x = lerp(x_from, x_to, clamp(self.lane_blend, 0.0, 1.0))
        else:
            x = lane_center_x_at_y(self.lane, y)

        # scale based on depth (near = bigger)
        scale = lerp(0.35, 1.10, self.z)
        w = int(self.base_w * scale)
        h = int(self.base_h * scale)

        rect = pygame.Rect(0, 0, w, h)
        rect.centerx = int(x)
        rect.bottom = int(y)  # feet on the road
        return rect

    def draw(self, surf):
        pygame.draw.rect(surf, (60, 220, 90), self.screen_rect(), border_radius=10)

class Obstacle:
    def __init__(self, lane, z, kind="block"):
        self.lane = lane
        self.z = z
        self.kind = kind
        self.base_w = 70
        self.base_h = 70 if kind == "block" else 55

    def update(self, dz):
        self.z += dz

    def screen_rect(self):
        y = y_from_z(self.z)
        x = lane_center_x_at_y(self.lane, y)

        scale = lerp(0.25, 1.20, self.z)
        w = int(self.base_w * scale)
        h = int(self.base_h * scale)

        rect = pygame.Rect(0, 0, w, h)
        rect.center = (int(x), int(y - h * 0.15))  # slight lift so it "sits" on road
        return rect

    def draw(self, surf):
        color = (220, 80, 80) if self.kind == "block" else (220, 220, 80)
        pygame.draw.rect(surf, color, self.screen_rect(), border_radius=8)

def draw_road(surf):
    # trapezoid road
    far_left = ROAD_CENTER_X - ROAD_FAR_W // 2
    far_right = ROAD_CENTER_X + ROAD_FAR_W // 2
    near_left = ROAD_CENTER_X - ROAD_NEAR_W // 2
    near_right = ROAD_CENTER_X + ROAD_NEAR_W // 2

    road_poly = [(far_left, ROAD_FAR_Y), (far_right, ROAD_FAR_Y),
                 (near_right, ROAD_NEAR_Y), (near_left, ROAD_NEAR_Y)]
    pygame.draw.polygon(surf, (40, 40, 45), road_poly)

    # road edges
    pygame.draw.lines(surf, (90, 90, 95), True, road_poly, 3)

    # lane separators (perspective)
    for i in range(1, LANES):
        # line from far to near at lane boundary
        # compute boundary x at far and near
        far_lane_w = ROAD_FAR_W / LANES
        near_lane_w = ROAD_NEAR_W / LANES
        x_far = (ROAD_CENTER_X - ROAD_FAR_W / 2) + far_lane_w * i
        x_near = (ROAD_CENTER_X - ROAD_NEAR_W / 2) + near_lane_w * i
        pygame.draw.line(surf, (70, 70, 75), (x_far, ROAD_FAR_Y), (x_near, ROAD_NEAR_Y), 2)

    # dashed center guide (pure juice)
    dash_count = 18
    for k in range(dash_count):
        t0 = k / dash_count
        t1 = (k + 0.5) / dash_count
        y0 = lerp(ROAD_FAR_Y, ROAD_NEAR_Y, t0)
        y1 = lerp(ROAD_FAR_Y, ROAD_NEAR_Y, t1)
        x0 = ROAD_CENTER_X
        # fade dashes into the distance
        alpha = int(lerp(40, 180, t0))
        pygame.draw.line(surf, (alpha, alpha, alpha), (x0, y0), (x0, y1), 3)

def main():
    player = Player()
    obstacles = []

    score = 0
    alive = True

    # Movement in depth per frame (bigger = faster)
    base_speed = 0.010
    speed = base_speed

    # spawn cadence
    spawn_cooldown = 0

    while True:
        dt = clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

                if alive:
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        player.move_left()
                    if event.key in (pygame.K_RIGHT, pygame.K_d):
                        player.move_right()
                else:
                    if event.key == pygame.K_r:
                        return main()

        if alive:
            # ----- UPDATE -----
            player.update()

            # difficulty ramp
            score += 1
            if score % 500 == 0:
                speed += 0.0012

            # spawn obstacles
            spawn_cooldown -= 1
            if spawn_cooldown <= 0:
                # Simple fairness: never spawn all 3 lanes at once.
                # Either 1 obstacle or sometimes 2.
                lanes = [0, 1, 2]
                random.shuffle(lanes)
                count = 2 if random.random() < 0.25 else 1

                for i in range(count):
                    lane = lanes[i]
                    z0 = random.uniform(Z_SPAWN_MIN, Z_SPAWN_MAX)
                    obstacles.append(Obstacle(lane, z0, kind="block"))

                spawn_cooldown = random.randint(25, 45)

            # move obstacles toward player
            for obs in obstacles:
                obs.update(speed)

            # remove passed obstacles
            obstacles = [o for o in obstacles if o.z < 1.15]

            # collision: compare screen rects when obstacle is near-ish
            p_rect = player.screen_rect()
            for obs in obstacles:
                if obs.z > 0.70:  # only check when close to player
                    if p_rect.colliderect(obs.screen_rect()):
                        alive = False
                        break

        # ----- DRAW -----
        screen.fill((18, 18, 22))
        draw_road(screen)

        # draw obstacles from far to near (so near ones appear on top)
        for obs in sorted(obstacles, key=lambda o: o.z):
            obs.draw(screen)

        player.draw(screen)

        # UI
        ui = FONT.render(f"Score: {score}   Speed: {speed:.3f}", True, (235, 235, 235))
        screen.blit(ui, (16, 14))

        if not alive:
            msg = FONT.render("Game Over — press R to restart", True, (255, 255, 255))
            screen.blit(msg, (W // 2 - msg.get_width() // 2, H // 2))

        pygame.display.flip()

if __name__ == "__main__":
    main()
