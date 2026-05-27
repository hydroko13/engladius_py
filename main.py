import asyncio
import pygame
import struct

class Game:
    def __init__(self):

        self.base_size = (320, 180)

        mon_idx = 0
        self.window = pygame.display.set_mode(pygame.display.get_desktop_sizes()[mon_idx], flags=pygame.FULLSCREEN, display=mon_idx)
        self.game_surf = pygame.Surface(self.base_size).convert()
        self.clock = pygame.time.Clock()
        self.dt = 0.0
        self.fps = 60.0
        self.done = False

        self.incoming_queue = asyncio.Queue()
        self.outgoing_queue = asyncio.Queue()

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

    async def run(self):

        server_reader, server_writer = await asyncio.open_connection('127.0.0.1', 9999)

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
                    
                    print(packet)
                    
                    packets.append(packet)
                    
                except asyncio.QueueEmpty:
                    break
                
            for packet in packets:
                print(packet)
                
            self.window.fill((0, 0, 0))
            self.game_surf.fill((15, 40, 36))

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
