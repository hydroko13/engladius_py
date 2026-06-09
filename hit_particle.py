import pygame
import math
import random

class HitParticle:
    def __init__(self, x, y, angle):
        self.pos = [x, y]
        self.vx = math.cos(math.radians(angle + random.uniform(-20, 20)))
        self.vy = math.sin(math.radians(angle + random.uniform(-20, 20)))
        self.l = 0
        self.ml = 0.9 + random.uniform(-0.12, 0.12)
        self.flicker_threshold = 0.3
        self.flicker_state = False
        self.flicker_tick = 0.0
        
        
        
        
        
    def draw(self, surf, cam):
        
        if self.flicker_state or self.l < self.flicker_threshold:     
            p = cam.offset_point(self.pos)
            pygame.draw.circle(surf, (230, 13, 2), p, 1)
            
    def update(self, delta):
        dt = delta * 1.1
        self.pos[0] += self.vx * dt * max([(29 - math.exp(self.l * 5.8) * 0.6), 0])
        self.pos[1] += self.vy * dt * max([(29 - math.exp(self.l * 5.8) * 0.6), 0])
        self.l += dt
        if self.l > self.flicker_threshold:
            if self.flicker_tick > 0.02:
                self.flicker_state = not self.flicker_state
                self.flicker_tick = 0
            self.flicker_tick += dt
        
        
        