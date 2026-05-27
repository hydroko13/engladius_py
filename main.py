import asyncio
import pygame
import struct
from player import Player
import socket

class Game:
    def __init__(self):

        self.base_size = (480, 270)

        mon_idx = 0
        self.window = pygame.display.set_mode(pygame.display.get_desktop_sizes()[mon_idx], flags=pygame.FULLSCREEN, display=mon_idx, vsync=1)
        self.game_surf = pygame.Surface(self.base_size).convert()
        self.clock = pygame.time.Clock()
        self.dt = 0.0
        self.fps = 60.0
        self.done = False

        self.incoming_queue = asyncio.Queue()
        self.outgoing_queue = asyncio.Queue()

        self.player = Player(self.base_size[0]/2, self.base_size[1]/2, True)
        self.other_players = {}
        self.pos_broadcast_tick = 0.0
        self.pos_broadcast_rate = 40

    async def read_loop(self, server_reader):
        try:
            while True:
                try:
                    packet_size_bytes = await server_reader.readexactly(4)
                    packet_size, = struct.unpack("!I", packet_size_bytes)
                    data = await server_reader.readexactly(packet_size)
                    self.incoming_queue.put_nowait(data)
                except asyncio.IncompleteReadError:
                    self.done = True
                    break

        except asyncio.CancelledError:
            pass

    async def write_loop(self, server_writer):
        try:
            while True:

                data = await self.outgoing_queue.get()

                if data is None:
                    break

                packet = struct.pack('!I', len(data))

                server_writer.write(packet + data)
                
                await server_writer.drain()
                
        except asyncio.CancelledError:
            pass

    def draw(self):
        self.player.draw(self.game_surf)
        for i, p in self.other_players.items():
            p.draw(self.game_surf)

    def update(self):
        self.player.update(self.dt)
        for i, p in self.other_players.items():
            p.update(self.dt)

        if self.pos_broadcast_tick >= 1 / self.pos_broadcast_rate:
            self.outgoing_queue.put_nowait(b'p' + struct.pack('!ii', int(self.player.pos[0]), int(self.player.pos[1])))
            self.pos_broadcast_tick = 0.0
        self.pos_broadcast_tick += self.dt

        

    async def run(self):

        server_reader, server_writer = await asyncio.open_connection('127.0.0.1', 9999)

        sock = server_writer.get_extra_info("socket")
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        read_task = asyncio.create_task(self.read_loop(server_reader))
        write_task = asyncio.create_task(self.write_loop(server_writer))

        while not self.done:

            self.dt = self.clock.tick(self.fps) / 1000
            await asyncio.sleep(0)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.done = True
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.done = True
                        
            packets = []
                        
            while True:
                try:
                    packet = self.incoming_queue.get_nowait()
                    
                    packets.append(packet)
                    
                except asyncio.QueueEmpty:
                    break
                
            for packet in packets:
                first_byte = packet[:1]
                if first_byte == b'p':
                    i, x, y = struct.unpack_from('!Iii', packet[1:])

                    if i not in self.other_players:
                        self.other_players[i] = Player(0, 0)
                    print(x, y)
                    self.other_players[i].target = [x, y]
            
                
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

        await self.outgoing_queue.put(None)

        read_task.cancel()
        write_task.cancel()

        await asyncio.gather(read_task, write_task)

        server_writer.close()
        await server_writer.wait_closed()


async def main():
    print("Engladius client v0.1")
    pygame.init()
    game = Game()
    await game.run()
    
    
    
    pygame.quit()


if __name__ == '__main__':
    asyncio.run(main())
