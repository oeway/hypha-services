import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from imjoy_rpc.hypha import connect_to_server
import time

def convert_sync_to_async(sync_func, loop, executor):
    async def wrapped_async(*args, **kwargs):
        result_future = loop.create_future()

        def run_and_set_result():
            try:
                result = sync_func(*args, **kwargs)
                loop.call_soon_threadsafe(result_future.set_result, result)
            except Exception as e:
                loop.call_soon_threadsafe(result_future.set_exception, e)

        executor.submit(run_and_set_result)
        result = await result_future
        obj = _encode_callables(result, convert_async_to_sync, loop, executor)
        return obj

    return wrapped_async


def convert_async_to_sync(async_func, loop, executor):
    def wrapped_sync(*args, **kwargs):
        # Recursively encode callables in args
        args = _encode_callables(args, convert_sync_to_async, loop, executor)

        # Recursively encode callables in kwargs
        kwargs = _encode_callables(kwargs, convert_sync_to_async, loop, executor)

        async def func_async():
            return await async_func(*args, **kwargs)

        return asyncio.run_coroutine_threadsafe(func_async(), loop).result()

    return wrapped_sync


def _encode_callables(obj, wrap, loop, executor):
    if isinstance(obj, dict):
        return {k: _encode_callables(v, wrap, loop, executor) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_encode_callables(item, wrap, loop, executor) for item in obj]
    elif callable(obj):
        return wrap(obj, loop, executor)
    else:
        return obj

class SyncHyphaServer:
    def __init__(self):
        self.loop = None
        self.thread = None
        self.server = None
        self.executor = ThreadPoolExecutor(max_workers=1)

    async def _connect_to_server(self, config):
        self.server = await connect_to_server(config)
        print(f"Services registered at workspace: {self.server.config.workspace}")
        print(f"Test them with the HTTP proxy: {self.server.config.public_base_url}/{self.server.config.workspace}/services/hello-world/hello?name=World")
        obj = _encode_callables(self.server, convert_async_to_sync, self.loop, self.executor)
        # for every key in obj, set it as an attribute of self
        assert isinstance(obj, dict), "The server object must be a dict"
        for(k, v) in obj.items():
            setattr(self, k, v)

    def _start_loop(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        self.loop = asyncio.get_event_loop()
        self.loop.run_forever()


def connect_to_server_sync(config):
    server = SyncHyphaServer()

    if not server.loop:
        server.thread = threading.Thread(target=server._start_loop, daemon=True)
        server.thread.start()

    while not server.loop or not server.loop.is_running():
        pass  # Wait until loop is running

    future = asyncio.run_coroutine_threadsafe(server._connect_to_server(config), server.loop)
    future.result()  # Wait for the server to start

    return server


if __name__ == "__main__":
    server_url = "https://ai.imjoy.io"
    server = connect_to_server_sync({"server_url": server_url})

    def hello(name):
        print("Hello " + name)
        # print the current thread id, check if it's the mainthread
        print("Current thread id: ", threading.get_ident(), threading.current_thread())
        time.sleep(20)
        return "Hello " + name

    server.register_service({
        "name": "Hello World",
        "id": "hello-world",
        "config": {
            "visibility": "public",
            "run_in_executor": True,
        },
        "hello": hello
    })
    
    services = server.list_services("public")
    print("Public Services: ", services)

    while True:
        print('.', end='', flush=True)
        time.sleep(1)
