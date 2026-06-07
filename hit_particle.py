import pygame
import math
import random

class HitParticle:
    def __init__(self, x, y, angle):
        self.pos = [x, y]
        self.vx = math.cos(math.radians(angle + random.uniform(-20, 20)))
        self.vy = math.sin(math.radians(angle + random.uniform(-20, 20)))
        self.l = 0
        self.ml = random.uniform(1.3, 1.7)
        self.flicker_threshold = 0.9
        self.flicker_state = False
        self.flicker_tick = 0.0
        
        
        
        
        
    def draw(self, surf, cam):
        
        if self.flicker_state or self.l < self.flicker_threshold:     
            p = cam.offset_point(self.pos)
            pygame.draw.circle(surf, (230, 13, 2), p, 1)
            
    def update(self, dt):
        self.pos[0] += self.vx * dt * (29 - math.exp(self.l * 1.3) * 0.6)
        self.pos[1] += self.vy * dt * (29 - math.exp(self.l * 1.3) * 0.6)
        self.l += dt
        if self.l > self.flicker_threshold:
            if self.flicker_tick > 0.02:
                self.flicker_state = not self.flicker_state
                self.flicker_tick = 0
            self.flicker_tick += dt
        
        
        
        