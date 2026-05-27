import asyncio
import struct


class ClientDisconnected(Exception):
    pass


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

async def client_update_loop(incoming_queue, outgoing_queue):
    cancelled = False
    try:
        while True:

            outgoing_queue.put_nowait(b'hey')
            
            await asyncio.sleep(0.04)

            
        
    except asyncio.CancelledError:
        cancelled = True
        
    if not cancelled:
        raise ClientDisconnected()

async def handle_client(reader, writer):
    address = writer.get_extra_info('peername')

    incoming_queue = asyncio.Queue()
    outgoing_queue = asyncio.Queue()

    print(f"Client at addr {address} connected")
    try:
        async with asyncio.TaskGroup() as tg:

            read_task = tg.create_task(client_read_loop(reader, incoming_queue))
            write_task = tg.create_task(client_write_loop(writer, outgoing_queue))
            loop_task = tg.create_task(client_update_loop(incoming_queue, outgoing_queue))
            
            
            
    except* ClientDisconnected:
        pass

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
