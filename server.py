import asyncio
import struct
from dataclasses import dataclass
import socket
import time

def find_mex(numbers):
    num_set = set(numbers)
    
    mex = 0
    while mex in num_set:
        mex += 1
        
    return mex

@dataclass
class Player:
    x: int
    y: int


class ClientDisconnected(Exception):
    pass

players = {}

async def read_loop(reader, player_id):
    global players
    while True:

        try:
            (packet_size,) = struct.unpack("!I", await reader.readexactly(4))

            packet = await reader.readexactly(packet_size)

            header = packet[:1]

            if header == b'p':
                x, y = struct.unpack_from(b'!ii', packet[1:])

                players[player_id].x = x
                players[player_id].y = y
            

        except (ConnectionError, asyncio.IncompleteReadError):
            break


async def write_loop(writer, player_id):
    global players
    while True:

        try:

            players_snapshot = list(players.items())

            for other_player_id, other_player in players_snapshot:
                if other_player_id != player_id and other_player_id in players:
                    buf = b"p" + struct.pack(
                        "!Iii",
                        other_player_id,
                        int(other_player.x),
                        int(other_player.y),
                    )
                    writer.write(struct.pack("!I", len(buf)) + buf)

            await writer.drain()
            await asyncio.sleep(0.05)

        except (ConnectionError, BrokenPipeError):
            break


async def handle_client(reader, writer):
    global players

    sock = writer.get_extra_info("socket")
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    address = writer.get_extra_info('peername')

    print(f"Client at addr {address} connected")
    player_id = find_mex(players.keys())
    players[player_id] = Player(0, 0)

    read_loop_task = asyncio.create_task(read_loop(reader, player_id))

    write_loop_task = asyncio.create_task(write_loop(writer, player_id))

    await asyncio.wait([read_loop_task, write_loop_task], return_when=asyncio.FIRST_COMPLETED)

    del players[player_id]

    print(f"Closing connection to {address}")
    try:
        writer.close()
        await writer.wait_closed()
    except ConnectionError:
        pass

async def main():
    server = await asyncio.start_server(handle_client, '127.0.0.1', 9999)
    
    async with server:
        print("Server running on 127.0.0.1:9999")
        
        await server.serve_forever()


if __name__ == '__main__':
    asyncio.run(main())
