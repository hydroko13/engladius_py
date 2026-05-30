import socket
import struct
import threading
import time
from dataclasses import dataclass
import typing
from collections import deque
import math


def recv_exact(sock, n_bytes):
    buffer = bytearray()
    while len(buffer) < n_bytes:
        remaining = n_bytes - len(buffer)
        
        chunk = sock.recv(remaining)
        
        if not chunk:
            raise ConnectionAbortedError()
            
        buffer.extend(chunk)
        
    return bytes(buffer)


class SwordJab:
    def __init__(self, pos, direction, player_id, world_id):
        self.direction = direction
        self.pos = pos
        self.extension_offset = 5
        self.state = 0
        self.dx = 0
        self.dy = 0
        self.player_id = player_id
        self.world_id = world_id
        self.hit_something = False
        
        if self.direction == 'right':
            self.dx = 1
            self.dy = 0
        elif self.direction == 'left':
            self.dx = -1
            self.dy = 0
        elif self.direction == 'up':
            self.dy = -1
            self.dx = 0
        elif self.direction == 'down':
            self.dy = 1
            self.dx = 0

    def update(self, dt):
        if self.state == 0:
            self.extension_offset += dt * 100
            if self.extension_offset > 18:
                self.state = 1
        elif self.state == 1:
            self.extension_offset -= dt * 80
            if self.extension_offset <= 5:
                self.state = 2

    def get_collision_points(self):
        collide_points = []
        offx = (self.dx * self.extension_offset)
        offy = (self.dy * self.extension_offset)
        for i in range(-4, 8, 2):
            collide_points.append((self.pos[0] + offx + self.dx * i, self.pos[1] + offy + self.dy * i))
        return collide_points
    


@dataclass
class MatchJoinNpc:
    x: int
    y: int
    gamemode: int

@dataclass
class Player:
    x: int
    y: int
    world_id: int
    to_broadcast_join: deque
    to_broadcast_left: deque
    to_broadcast_gameevents: deque


def find_mex(numbers):
    num_set = set(numbers)
    mex = 0

    while mex in num_set:
        mex += 1
        
    return mex


class Server:
    def __init__(self):
        self.kill_event = threading.Event()
        self.players = {

        }
        self.players_lock = threading.Lock()

        self.worlds = set([0])

        self.match_join_npcs = []

        self.match_join_npcs.append(MatchJoinNpc(30, -42, 0))

        self.match_join_npcs_lock = threading.Lock()

        self.sword_jabs = []
        self.sword_jabs_lock = threading.Lock()


        # World 0 is always the main lobby

    def handle_client(self, conn, addr, kill_event):

        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        player_id = None

        with self.players_lock:
            player_id = find_mex(self.players.keys())    
            print(f'Player {addr} (id: {player_id}) joined.')   
            already_joined = self.players.items()

            self.players[player_id] = Player(0, 0, 0, deque([(k, v.world_id) for k, v in already_joined]), deque(), deque()) # x, y, world, etc... (the 3rd zero is the world_id)
            for player_id2, player in self.players.items():
                if player_id2 != player_id:
                    self.players[player_id2].to_broadcast_join.append((player_id, 0)) # join world 0
        try:
            conn.sendall(struct.pack('!I', player_id))

            while not kill_event.is_set():

                x, y = struct.unpack('!ii', recv_exact(conn, 8))
                player_positions = {}
                to_broadcast_join = []
                to_broadcast_left = []
                to_broadcast_gameevents = []
                with self.players_lock:
                    self.players[player_id].x = x
                    self.players[player_id].y = y
                    current_world = self.players[player_id].world_id
                    for i, p in self.players.items():
                        if p.world_id == current_world:
                            player_positions[i] = (p.x, p.y)

                    while len(self.players[player_id].to_broadcast_join) > 0:
                        joined_id, world_id = self.players[player_id].to_broadcast_join.popleft()
                        if world_id == current_world:
                            to_broadcast_join.append(joined_id)
                    while len(self.players[player_id].to_broadcast_left) > 0:
                        left_id, world_id = self.players[player_id].to_broadcast_left.popleft()
                        if world_id == current_world:
                            to_broadcast_left.append(left_id)
                    while len(self.players[player_id].to_broadcast_gameevents) > 0:
                        event_data, world_id = self.players[
                            player_id
                        ].to_broadcast_gameevents.popleft()
                        if world_id == current_world:
                            to_broadcast_gameevents.append(event_data)

                count_joined = len(to_broadcast_join)

                conn.sendall(struct.pack('!I', count_joined))

                for player_joined_id in to_broadcast_join:
                    conn.sendall(struct.pack('!I', player_joined_id))

                count_left = len(to_broadcast_left)

                conn.sendall(struct.pack('!I', count_left))

                for player_left_id in to_broadcast_left:
                    conn.sendall(struct.pack('!I', player_left_id))

                count_events = len(to_broadcast_gameevents)

                conn.sendall(struct.pack("!I", count_events))

                for e in to_broadcast_gameevents:
                    conn.sendall(struct.pack("!I", len(e)))
                    conn.sendall(e)

                len_sent_events = struct.unpack('!I', recv_exact(conn, 4))[0]
                sent_new_events = []

                for i in range(len_sent_events):
                    len_event = struct.unpack("!I", recv_exact(conn, 4))[0]
                    event = recv_exact(conn, len_event)
                    sent_new_events.append(event)

                for e in sent_new_events:
                    if e[:1] == b'A':
                        attack_id, x, y, direction = struct.unpack('!BiiB', e[1:])

                        if attack_id == 0:

                            direction_string = ''
                            if direction == 0: 
                                direction_string = 'left'
                            elif direction == 1: 
                                direction_string = 'right'
                            elif direction == 2: 
                                direction_string = 'down'
                            elif direction == 3: 
                                direction_string = 'up'

                            with self.sword_jabs_lock:
                                swordjab = SwordJab([x, y], direction_string, player_id, current_world)
                                self.sword_jabs.append(swordjab)

                            with self.players_lock:
                                for player_id2 in self.players.keys():
                                    if player_id2 != player_id:
                                        self.players[
                                            player_id2
                                        ].to_broadcast_gameevents.append(
                                            (e, current_world)
                                        )

                players_count = len(player_positions)
                conn.sendall(struct.pack('!I', players_count))

                for player_id2, pos in player_positions.items():
                    conn.sendall(struct.pack('!Iii', player_id2, pos[0], pos[1]))


                time.sleep(0.01)
        except ConnectionError:
            pass

        print(f'Player {addr} (id: {player_id}) left.')
        with self.players_lock:
            w = self.players[player_id].world_id

            del self.players[player_id]
            for player_id2, player in self.players.items():
                self.players[player_id2].to_broadcast_left.append((player_id, w))
    
    def server_update_loop(self, kill_event):
        last_time = time.monotonic()
        dt = 0
        while not kill_event.is_set():

            match_join_positions = []

            with self.match_join_npcs_lock:
                for npc in self.match_join_npcs:
                    match_join_positions.append((npc.x, npc.y, npc.gamemode))

            gamemodes_requested_join = []

            with self.sword_jabs_lock:
                for s in self.sword_jabs:
                    s.update(dt)
                self.sword_jabs = [s for s in self.sword_jabs if s.state != 2]
            
                for npc_pos in match_join_positions:
                    
                    gamemode = npc_pos[2]
                    for idx, s in enumerate(self.sword_jabs):
                        hit = False
                        if (not s.hit_something) and s.world_id == 0:
                            collide_points = s.get_collision_points()
                            for c in collide_points:
                                distance = math.dist(c, (npc_pos[0], npc_pos[1]))
                                if distance <= 8.3:
                                    hit = True
                                    break
                        if hit:
                            
                            self.sword_jabs[idx].hit_something = True
                            gamemodes_requested_join.append((gamemode, s.player_id))
            with self.players_lock:
                for join_request in gamemodes_requested_join:
                    
                    dest_world = 1
                    src_world = 0 # always zero in this case because people can only join games from the main lobby

                    self.players[join_request[1]].world_id = dest_world

                    for pid, player in self.players.items():
                        if pid != join_request[1]:
                            if player.world_id == src_world:
                                self.players[pid].to_broadcast_left.append((join_request[1], src_world))

                    for pid, player in self.players.items():
                        if pid != join_request[1]:
                            if player.world_id == dest_world:
                                self.players[pid].to_broadcast_join.append((join_request[1], dest_world))
                    for pid, player in self.players.items():
                        if pid != join_request[1]:
                            if player.world_id == dest_world:
                                self.players[join_request[1]].to_broadcast_join.append((pid, dest_world))


            dt = time.monotonic() - last_time
            last_time = time.monotonic()
            time.sleep(0.065)

    def run(self):
        update_thread = threading.Thread(target=self.server_update_loop, args=(self.kill_event, ))
        update_thread.start()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            print("Starting server on 0.0.0.0:9999")
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', 9999))
            s.listen()
            threads = []
            while True:
                conn, addr = s.accept()
                thread = threading.Thread(target=self.handle_client, args=(conn, addr, self.kill_event))
                thread.start()
                threads.append(thread)


if __name__ == '__main__':
    server = Server()
    server.run()
