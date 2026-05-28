import socket
import struct
import threading
import time
from dataclasses import dataclass
import typing
from collections import deque


def recv_exact(sock, n_bytes):
    buffer = bytearray()
    while len(buffer) < n_bytes:
        remaining = n_bytes - len(buffer)
        
        chunk = sock.recv(remaining)
        
        if not chunk:
            raise ConnectionAbortedError()
            
        buffer.extend(chunk)
        
    return bytes(buffer)


@dataclass
class Player:
    x: int
    y: int
    to_broadcast_join: deque
    to_broadcast_left: deque


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

    def handle_client(self, conn, addr, kill_event):
        

        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        player_id = None
        with self.players_lock:
            player_id = find_mex(self.players.keys())    
            print(f'Player {addr} (id: {player_id}) joined.')   
            already_joined = list(self.players.keys())

            self.players[player_id] = Player(0, 0, deque(already_joined), deque())
            for player_id2, player in self.players.items():
                if player_id2 != player_id:
                    self.players[player_id2].to_broadcast_join.append(player_id)
            
        try:
            conn.sendall(struct.pack('!I', player_id))

            while not kill_event.is_set():

                x, y = struct.unpack('!ii', recv_exact(conn, 8))
                player_positions = {}
                to_broadcast_join = []
                to_broadcast_left = []
                with self.players_lock:
                    self.players[player_id].x = x
                    self.players[player_id].y = y
                    for i, p in self.players.items():
                        player_positions[i] = (p.x, p.y)
                    
                    while len(self.players[player_id].to_broadcast_join) > 0:
                        to_broadcast_join.append(self.players[player_id].to_broadcast_join.popleft())
                    while len(self.players[player_id].to_broadcast_left) > 0:
                        to_broadcast_left.append(self.players[player_id].to_broadcast_left.popleft())


                count_joined = len(to_broadcast_join)

                conn.sendall(struct.pack('!I', count_joined))

                for player_joined_id in to_broadcast_join:
                    conn.sendall(struct.pack('!I', player_joined_id))

                count_left = len(to_broadcast_left)

                conn.sendall(struct.pack('!I', count_left))

                for player_left_id in to_broadcast_left:
                    conn.sendall(struct.pack('!I', player_left_id))



                

                players_count = len(player_positions)
                conn.sendall(struct.pack('!I', players_count))
                

                for player_id2, pos in player_positions.items():
                    conn.sendall(struct.pack('!Iii', player_id2, pos[0], pos[1]))
                
                    
                time.sleep(0.01)
        except ConnectionError:
            pass



        print(f'Player {addr} (id: {player_id}) left.')
        with self.players_lock:
            del self.players[player_id]
            for player_id2, player in self.players.items():
                self.players[player_id2].to_broadcast_left.append(player_id)

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            print("Starting server on 127.0.0.1:9999")
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('127.0.0.1', 9999))
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