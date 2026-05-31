import threading
import pygame
import struct
from player import Player
import socket
import time
from camera import Camera
from sword_jab import SwordJab
import queue
import os

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
        windowed = False



        if windowed:
            self.window = pygame.display.set_mode(
                (960, 540),
                display=mon_idx,
                vsync=1,
            )
        else:
            self.window = pygame.display.set_mode(pygame.display.get_desktop_sizes()[mon_idx], flags=pygame.FULLSCREEN, display=mon_idx)
        self.game_surf = pygame.Surface(self.base_size).convert()
        self.grass_tile = pygame.image.load(os.path.join('assets', 'grass_tile.png')).convert()
        self.clock = pygame.time.Clock()
        self.dt = 0.0
        self.fps = 60.0
        self.done = False
        self.kill_event = threading.Event()
        self.crash_event = threading.Event()
        self.player = Player(0, 0, True)
        self.player_lock = threading.Lock()
        self.other_players_lock = threading.Lock()
        self.other_players = {}
        self.cam = Camera()
        self.player_id = None
        self.sword_jabs = []
        self.events_to_server_queued = queue.Queue()
        self.other_player_sword_jabs = []
        self.other_player_sword_jabs_lock = threading.Lock()
        self.tilemap_layer_surfaces = []
        self.mic_chunk_size = 400



        tilesurf = pygame.Surface((16*200, 16*200)).convert()

        for x in range(0, 200):
            for y in range(0, 200):
                pos = (x * 16, y * 16)
                tilesurf.blit(self.grass_tile, pos)

        self.tilemap_layer_surfaces.append(tilesurf)


    def draw(self):

        for l in self.tilemap_layer_surfaces:
            self.game_surf.blit(l, self.cam.offset_point((-100 * 16, -100 * 16)))

        for j in self.sword_jabs:
            j.draw(self.game_surf, self.cam)

        with self.other_player_sword_jabs_lock:
            for j in self.other_player_sword_jabs:
                j.draw(self.game_surf, self.cam)

        with self.player_lock:
            self.player.draw(self.game_surf, self.cam)
        with self.other_players_lock:
            for i, p in self.other_players.items():
                p.draw(self.game_surf, self.cam)
        pygame.draw.circle(self.game_surf, (100, 200, 0), self.cam.offset_point([30, -42]), 8)
        pygame.draw.circle(self.game_surf, (11, 25, 11), self.cam.offset_point([30, -42]), 8, 1)

    def update(self):
        f = False
        for j in self.sword_jabs:
            j.update(self.dt)
            if j.state == 2:
                f = True

        self.sword_jabs = [j for j in self.sword_jabs if j.state != 2]

        with self.other_player_sword_jabs_lock:
            for j in self.other_player_sword_jabs:
                j.update(self.dt)

            self.other_player_sword_jabs = [
                j for j in self.other_player_sword_jabs if j.state != 2
            ]

        p = None
        with self.player_lock:
            self.player.update(self.dt)
            p = self.player.pos[:]
            if f:
                self.player.attacking = False
        self.cam.update(p, self.dt)
        with self.other_players_lock:
            for i, p in self.other_players.items():
                p.update(self.dt)


    

    def sender_network_thread(self, kill_event, crash_event, s):
        try:

            last_time = time.monotonic()

            while not kill_event.is_set():

                t = time.monotonic()
                dt = t - last_time
                last_time = time.monotonic()
                player_pos = None
                with self.player_lock:
                    player_pos = (self.player.pos[0], self.player.pos[1])

                s.sendall(struct.pack('!ii', int(player_pos[0]), int(player_pos[1])))


                events_to_send = []
                while True:
                    try:
                        events_to_send.append(self.events_to_server_queued.get_nowait())
                    except queue.Empty:
                        break

                s.sendall(struct.pack('!I', len(events_to_send)))

                for e in events_to_send:
                    s.sendall(struct.pack("!I", int(len(e))) + e)

                time.sleep(0.01)

        except ConnectionError:
            print("CRASHED DUE TO NETWORK ERROR")
            crash_event.set()
            pass

    def receiver_network_thread(self, kill_event, crash_event, s):
        try:
            

            
            last_time = time.monotonic()

            while not kill_event.is_set():

                t = time.monotonic()
                dt = t - last_time
                last_time = time.monotonic()

                joined_count = struct.unpack("!I", recv_exact(s, 4))[0]
                joined = []

                for _ in range(joined_count):
                    joined.append(struct.unpack("!I", recv_exact(s, 4))[0])

                left_count = struct.unpack("!I", recv_exact(s, 4))[0]
                left = []

                for _ in range(left_count):
                    left.append(struct.unpack("!I", recv_exact(s, 4))[0])

                event_count = struct.unpack("!I", recv_exact(s, 4))[0]
                new_events = []

                for _ in range(event_count):
                    l = struct.unpack("!I", recv_exact(s, 4))[0]
                    new_events.append(recv_exact(s, l))

                

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

                for e in new_events:
                    if e[:1] == b'A':
                        attack_byte, x, y, direction_byte = struct.unpack('!BiiB', e[1:])
                        direction_string = ''
                        if direction_byte == 0: 
                            direction_string = 'left'
                        elif direction_byte == 1: 
                            direction_string = 'right'
                        elif direction_byte == 2: 
                            direction_string = 'down'
                        elif direction_byte == 3: 
                            direction_string = 'up'

                        if attack_byte == 0: # SWORD

                            with self.other_player_sword_jabs_lock:
                                self.other_player_sword_jabs.append(
                                    SwordJab([x, y], direction_string)
                                )

                time.sleep(0.01)

        except ConnectionError:
            print("CRASHED DUE TO NETWORK ERROR")
            crash_event.set()
            pass

    def run(self):

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

            s.connect(("209.103.45.67", 9999))

            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            player_id = struct.unpack("!I", recv_exact(s, 4))[0]

            self.player_id = player_id

            send_thread = threading.Thread(target=self.sender_network_thread, args=(self.kill_event, self.crash_event, s))
            send_thread.start()
            recv_thread = threading.Thread(target=self.receiver_network_thread, args=(self.kill_event, self.crash_event, s))
            recv_thread.start()
            
            

            while not self.done:

                self.dt = self.clock.tick(30) / 1000

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.done = True
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self.done = True
                        if event.key == pygame.K_o:

                            pos = None
                            d = ''
                            can_attack = False
                            with self.player_lock:
                                pos = self.player.pos[:]
                                d = self.player.direction
                                can_attack = self.player.can_attack
                                if can_attack:
                                    self.player.attacking = True
                            if can_attack:
                                self.sword_jabs.append(SwordJab(pos, d))
                                db = None
                                if d == 'left':
                                    db = 0
                                elif d == 'right':
                                    db = 1
                                elif d == 'down':
                                    db = 2
                                elif d == 'up':
                                    db = 3
                                self.events_to_server_queued.put_nowait(
                                    b"A"
                                    + struct.pack("!BiiB", 0, int(pos[0]), int(pos[1]), db)
                                )

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
            recv_thread.join()
            send_thread.join()

if __name__ == '__main__':
    print("Engladius client v0.1")
    pygame.init()
    game = Game()
    
    
    game.run()
    
    pygame.quit()
