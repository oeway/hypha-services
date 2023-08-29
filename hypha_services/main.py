import asyncio
import base64
import hashlib
import hmac
import os
import socket
import time
from functools import partial

from imjoy_rpc.hypha import connect_to_server

from hypha_services.utils import pip_install


COTURN_SECRET = os.getenv("COTURN_SECRET")
assert COTURN_SECRET, "COTURN_SECRET is not set"
COTURN_PORT = os.getenv("COTURN_PORT", "3478")

pip_install("ray[default]")
pip_install("cloudpickle")
from hypha_services.ray_utils import register_function_launcher


if os.getenv("KUBERNETES_SERVICE_HOST"):
    pip_install("kubernetes")
    from kubernetes import client as k8s_client

    from hypha_services.k8s_utils import *

    config.load_incluster_config()

    client = k8s_client.CoreV1Api()
else:
    pip_install("docker")
    import docker

    from hypha_services.docker_utils import *

    client = docker.from_env()


def get_rtc_ice_servers(public_base_url, ttl=12 * 3600, context=None):
    """Get the RTC ice servers."""
    # TTL is the time to live in seconds
    user_name = context["user"]["id"]
    secret = COTURN_SECRET
    timestamp = int(time.time()) + ttl
    username = str(timestamp) + ":" + user_name
    dig = hmac.new(secret.encode(), username.encode(), hashlib.sha1).digest()
    credential = base64.b64encode(dig).decode()
    hostname = public_base_url.split("://")[1]

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)  # Timeout for the connect operation

    try:
        sock.connect((hostname, int(COTURN_PORT)))
    except socket.error as error:
        raise Exception(f"The coturn server ({hostname}:{COTURN_PORT}) is down")

    finally:
        sock.close()

    return [
        {
            "username": username,
            "credential": credential,
            "urls": [
                f"turn:{hostname}:{COTURN_PORT}",
                f"stun:{hostname}:{COTURN_PORT}",
            ],
        }
    ]


async def hypha_startup(server):
    """Hypha startup function for registering additional services."""
    # The server object is the same as the one in the client script
    # You can register more functions or call other functions in the server object
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, run_container_tests, client)
    except Exception as e:
        print("Failed to run docker tests:", e)
        loop.stop()

    await server.register_service(
        {
            "name": "Container Launcher",
            "id": "container-launcher",
            "config": {
                "visibility": "public",
                "require_context": False,
                "run_in_executor": True,
            },
            "run": partial(run_container, client),
            "exists": partial(exists_container, client),
            "logs": partial(logs_container, client),
            "list": partial(list_containers, client),
            "stop": partial(stop_container, client),
            "status": partial(status_container, client),
            "run_tests": partial(run_container_tests, client),
        }
    )
    print("Registered container launcher service")

    await server.register_service(
        {
            "id": "coturn",
            "config": {
                "visibility": "public",
                "require_context": True,
            },
            "get_rtc_ice_servers": partial(get_rtc_ice_servers, server.config['public_base_url']),
        }
    )
    print("Registered coturn service")

    await register_function_launcher(server, ray_address="ray://ray-head:10001")
    
    import cloudpickle

    launcher = await server.get_service("function-launcher")

    def run_cellpose(imgs_2D, channels):
        from cellpose import models, core

        use_GPU = core.use_gpu()
        print(">>> GPU activated? %d" % use_GPU)
        model = models.Cellpose(gpu=use_GPU, model_type="cyto")
        masks, flows, styles, diams = model.eval(
            imgs_2D, diameter=None, flow_threshold=None, channels=channels
        )
        return masks

    await launcher.deploy(
        "cellpose_predict",
        cloudpickle.dumps(run_cellpose),
        runtime_env={"pip": ["opencv-python-headless<4.3", "cellpose"]},
        num_gpus=1,
    )
    print("Registered ray function launcher service")


async def start_server(server_url):
    server = await connect_to_server(
        {"name": "hypha startup", "server_url": server_url}
    )
    await hypha_startup(server)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    task = loop.create_task(start_server(server_url="https://ai.imjoy.io"))
    loop.run_forever()
