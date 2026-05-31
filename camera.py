import pygame

class Camera:
    def __init__(self):
        self.pos = [0, 0]
        
    def update(self, target, dt):
        self.pos[0] += (target[0] - self.pos[0]) * dt * 16
        self.pos[1] += (target[1] - self.pos[1]) * dt * 16
    
    def offset_point(self, pos):
        return [pos[0] - self.pos[0] + 480 / 2, pos[1] - self.pos[1] + 270 / 2]