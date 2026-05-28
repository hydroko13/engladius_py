import threading
import pygame
import struct
from player import Player
import socket
import time


def recv_exact(sock, n_bytes):
    buffer = bytearray()
    while len(buffer) < n_bytes:
        remaining = n_bytes - len(buffer)
        
        chunk = sock.recv(remaining)
        
        if not chunk:
            raise ConnectionAbortedError()
            
        buffer.extend(chunk)
        
    return bytes(buffer)

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
        self.kill_event = threading.Event()
        self.crash_event = threading.Event()
        self.player = Player(self.base_size[0]/2, self.base_size[1]/2, True)
        self.player_lock = threading.Lock()
        self.other_players_lock = threading.Lock()
        self.other_players = {}
        self.player_id = None

    def draw(self):
        self.player.draw(self.game_surf)
        for i, p in self.other_players.items():
            p.draw(self.game_surf)

    def update(self):
        self.player.update(self.dt)
        for i, p in self.other_players.items():
            p.update(self.dt)


    def network_thread(self, kill_event, crash_event):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect(('127.0.0.1', 9999))

                s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

                player_id = struct.unpack("!I", recv_exact(s, 4))[0]

                self.player_id = player_id
                last_time = time.monotonic()


                while not kill_event.is_set():


                    t = time.monotonic()
                    dt = t - last_time
                    last_time = time.monotonic()
                    player_pos = None
                    with self.player_lock:
                        player_pos = (self.player.pos[0], self.player.pos[1])

                    s.sendall(struct.pack('!ii', int(player_pos[0]), int(player_pos[1])))

                    joined_count = struct.unpack("!I", recv_exact(s, 4))[0]
                    joined = []

                    for _ in range(joined_count):
                        joined.append(struct.unpack("!I", recv_exact(s, 4))[0])

                    left_count = struct.unpack("!I", recv_exact(s, 4))[0]
                    left = []

                    for _ in range(left_count):
                        left.append(struct.unpack("!I", recv_exact(s, 4))[0])



                    players_count = struct.unpack("!I", recv_exact(s, 4))[0]

                    for i in range(players_count):
                        other_player_id, x, y = struct.unpack("!Iii", recv_exact(s, 12))

                        if other_player_id in self.other_players:
                            self.other_players[other_player_id].target = [x, y]

                    with self.other_players_lock:

                        for j in joined:
                            self.other_players[j] = Player(0, 0)

                        for l in left:
                            del self.other_players[l]
                


                        

                        
                    
                    
                    

                    time.sleep(0.01)

            except ConnectionError:
                print("CRASHED DUE TO NETWORK ERROR")
                crash_event.set()
                pass


    def run(self):
        
        net_thread = threading.Thread(target=self.network_thread, args=(self.kill_event, self.crash_event))
        net_thread.start()

        while not self.done:

            self.dt = self.clock.tick(self.fps) / 1000

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.done = True
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.done = True

            if self.crash_event.is_set():
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

        self.kill_event.set()
        net_thread.join()

if __name__ == '__main__':
    print("Engladius client v0.1")
    pygame.init()
    game = Game()
    
    
    game.run()
    
    pygame.quit()