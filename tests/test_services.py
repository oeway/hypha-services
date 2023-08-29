import asyncio
import numpy as np
from imjoy_rpc.hypha import connect_to_server
import cloudpickle


async def hypha_startup(server):
    """Hypha startup function for registering additional services."""
    # The server object is the same as the one in the client script
    # You can register more functions or call other functions in the server object

    print("Running function launcher tests...")
    launcher = await server.get_service("function-launcher")
    await launcher.deploy("test", cloudpickle.dumps(lambda x: x + 1), num_gpus=0)
    assert await launcher.run("test", 1) == 2
    print("Function launcher test 1 passed!")

    print("cellpose_predict deployed!")
    images = [np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)]
    masks = await launcher.run("cellpose_predict", images, channels=[[2, 3]])
    assert len(masks) == 1
    assert masks[0].shape == images[0].shape[:2]
    print("Function launcher cellpose_predict test passed!")

    print("Running container launcher tests...")
    launcher = await server.get_service("container-launcher")
    # await launcher.run_tests()
    await launcher.stop("all")
    # await launcher.run("hypha-app-engine_imagej:latest", f"python run_imagej_service.py --server-url={server_info.public_base_url}", detach=True, environment={"DISPLAY": ":32" })
    # await launcher.run("ghcr.io/amun-ai/hypha:0.15.21", "python -m http.server 9382", detach=True)

    name = await launcher.run(
        "ubuntu",
        "echo hello world",
        detach=True,
    )
    assert "hello world" in await launcher.logs(name)
    await launcher.stop(name)

    print("Container launcher tests passed!")


async def start_server(server_url):
    server = await connect_to_server({"name": "test client", "server_url": server_url})
    await hypha_startup(server)


if __name__ == "__main__":
    asyncio.run(start_server(server_url="https://ai.imjoy.io"))
