import threading
import pygame
import struct
from player import Player
import socket

class Game:
    def __init__(self):

        self.base_size = (480, 270)

        mon_idx = 0
        windowed = True

        if windowed:
            self.window = pygame.display.set_mode(
                (960, 540),
                display=mon_idx,
                vsync=1,
            )
        else:
            self.window = pygame.display.set_mode(pygame.display.get_desktop_sizes()[mon_idx], flags=pygame.FULLSCREEN, display=mon_idx, vsync=1)
        self.game_surf = pygame.Surface(self.base_size).convert()
        self.clock = pygame.time.Clock()
        self.dt = 0.0
        self.fps = 60.0
        self.done = False

        self.player = Player(self.base_size[0]/2, self.base_size[1]/2, True)
        self.other_players = {}
        self.pos_broadcast_tick = 0.0
        self.pos_broadcast_rate = 40

    def draw(self):
        self.player.draw(self.game_surf)
        for i, p in self.other_players.items():
            p.draw(self.game_surf)

    def update(self):
        self.player.update(self.dt)
        for i, p in self.other_players.items():
            p.update(self.dt)

        if self.pos_broadcast_tick >= 1 / self.pos_broadcast_rate:
            self.pos_broadcast_tick = 0.0
        self.pos_broadcast_tick += self.dt

    def run(self):
        while not self.done:

            self.dt = self.clock.tick(self.fps) / 1000

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.done = True
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.done = True


            self.window.fill((0, 0, 0))
            self.game_surf.fill((0, 120, 100))

            self.update()

            self.draw()

            scaled_surf = pygame.transform.scale_by(
                self.game_surf,
                min(
                    [
                        self.window.get_size()[0] // self.base_size[0],
                        self.window.get_size()[1] // self.base_size[1],
                    ]
                ),
            )

            self.window.blit(scaled_surf, scaled_surf.get_rect(center=(self.window.get_size()[0] / 2, self.window.get_size()[1] / 2)))

            pygame.display.flip()
            
if __name__ == '__main__':
    print("Engladius client v0.1")
    pygame.init()
    game = Game()
    
    
    game.run()
    
    pygame.quit()