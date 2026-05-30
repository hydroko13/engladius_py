import pygame
import asyncio

class Player:
    def __init__(self, x, y, is_main=False):
        self.pos = [x, y]
        self.is_main = is_main
        self.target = [x, y]
        self.direction = 'right'
        self.attacking = False
        self.can_move = True
        self.can_attack = True
        self.attack_cooldown = 0.0

    def draw(self, surf, cam):
        pygame.draw.circle(surf, (0, 200, 0), cam.offset_point(self.pos), 8)
        pygame.draw.circle(surf, (11, 25, 11), cam.offset_point(self.pos), 8, 1)

    def update(self, dt):
        if self.is_main:
            if not self.attacking:
                self.attack_cooldown += dt
                if self.attack_cooldown > 0.12:
                    self.can_attack = True
                    self.can_move = True



            else:
                self.attack_cooldown = 0
                self.can_attack = False
                self.can_move = False

            if self.can_move:
                keys = pygame.key.get_pressed()
                if keys[pygame.K_a]:
                    self.pos[0] -= dt * 90
                    self.direction = 'left'
                if keys[pygame.K_d]:
                    self.pos[0] += dt * 90
                    self.direction = 'right'
                if keys[pygame.K_w]:
                    self.pos[1] -= dt * 90
                    self.direction = 'up'
                if keys[pygame.K_s]:
                    self.pos[1] += dt * 90
                    self.direction = 'down'

        else:
            self.pos[0] -= (self.pos[0] - self.target[0]) * dt * 24
            self.pos[1] -= (self.pos[1] - self.target[1]) * dt * 24
