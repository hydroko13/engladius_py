import pygame
import os

class SwordJab:
    def __init__(self, pos, direction):
        self.direction = direction
        self.pos = pos
        self.img = pygame.image.load(os.path.join('assets', 'sword.png'))
        self.extension_offset = 0
        self.state = 0


    def draw(self, surf, cam):
        img = None
        offx = 0
        offy = 0

        if self.direction == 'right':
            img = pygame.transform.rotate(self.img, -90)
            offx = self.extension_offset
            offy = 0
        elif self.direction == 'left':
            img = pygame.transform.rotate(self.img, 90)
            offx = -self.extension_offset
            offy = 0
        elif self.direction == 'up':
            img = self.img.copy()
            offx = 0
            offy = -self.extension_offset
        elif self.direction == 'down':
            img = pygame.transform.rotate(self.img, 180)
            offx = 0
            offy = self.extension_offset
        p = cam.offset_point(self.pos)
        surf.blit(img, (p[0] - 16 + offx, p[1] - 16 + offy))

    def update(self, dt):
        if self.state == 0:
            self.extension_offset += dt * 100
            if self.extension_offset > 18:
                self.state = 1
        elif self.state == 1:
            self.extension_offset -= dt * 80
            if self.extension_offset <= 0:
                self.state = 2
