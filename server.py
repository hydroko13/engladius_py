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

async def client_read_loop(reader, incoming):
    while True:

        try:
            packet_size, = struct.unpack("!I", await reader.readexactly(4))

            packet = await reader.readexactly(packet_size)

            incoming.put_nowait(packet)

        except (ConnectionError, asyncio.IncompleteReadError):
            break

    raise ClientDisconnected()


async def client_write_loop(writer, outgoing):
    cancelled = False
    try:
        while True:

            data = await outgoing.get()


            packet = struct.pack('!I', len(data))

            writer.write(packet + data)

            await writer.drain()
    except ConnectionError:
        pass
    except asyncio.CancelledError:
        cancelled = True
    if not cancelled:
        raise ClientDisconnected()

async def client_update_loop(incoming_queue, outgoing_queue, player_id):
    cancelled = False
    try:
        while True:

            start_time = time.monotonic()
            packets = []
                        
            while True:
                try:
                    packet = incoming_queue.get_nowait()
                    
                    packets.append(packet)
                    
                except asyncio.QueueEmpty:
                    break

            for packet in packets:
                first_byte = packet[:1]
                if first_byte == b'p':
                    x, y = struct.unpack_from(b'!ii', packet[1:])

                    players[player_id].x = x
                    players[player_id].y = y

            for other_player_id, other_player in players.items():
                if other_player_id != player_id:
                    outgoing_queue.put_nowait(b'p' + struct.pack('!Iii', other_player_id, int(other_player.x), int(other_player.y)))
            

            await asyncio.sleep(0.05)

            
            

            
        
    except asyncio.CancelledError:
        cancelled = True
        
    if not cancelled:
        raise ClientDisconnected()

async def handle_client(reader, writer):
    global players

    sock = writer.get_extra_info("socket")
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
    address = writer.get_extra_info('peername')

    incoming_queue = asyncio.Queue()
    outgoing_queue = asyncio.Queue()

    print(f"Client at addr {address} connected")
    player_id = find_mex(players.keys())
    players[player_id] = Player(0, 0)



    try:
        async with asyncio.TaskGroup() as tg:

            read_task = tg.create_task(client_read_loop(reader, incoming_queue))
            write_task = tg.create_task(client_write_loop(writer, outgoing_queue))
            loop_task = tg.create_task(client_update_loop(incoming_queue, outgoing_queue, player_id))
            
            
            
    except* ClientDisconnected:
        pass



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
