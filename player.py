import pygame
import asyncio

class Player:
    def __init__(self, x, y, is_main=False):
        self.pos = [x, y]
        self.is_main = is_main
        self.target = [x, y]

    def draw(self, surf):
        pygame.draw.circle(surf, (0, 200, 0), self.pos, 8)
        pygame.draw.circle(surf, (11, 25, 11), self.pos, 8, 1)

    def update(self, dt):
        if self.is_main:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_a]:
                self.pos[0] -= dt * 111
            if keys[pygame.K_d]:
                self.pos[0] += dt * 111
            if keys[pygame.K_w]:
                self.pos[1] -= dt * 111
            if keys[pygame.K_s]:
                self.pos[1] += dt * 111
        else:
            self.pos[0] -= (self.pos[0] - self.target[0]) * dt * 30
            self.pos[1] -= (self.pos[1] - self.target[1]) * dt * 30