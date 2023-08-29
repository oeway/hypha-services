from imjoy_rpc.hypha import connect_to_server
import asyncio
import argparse
import cloudpickle
import ray

function_registry = {}

async def register_function_launcher(server, ray_address=None):
    if ray_address:
        ray.init(address=ray_address)

    print(server.config)

    def deploy_function(function_id, serialized_function, context=None, **kwargs):
        f = cloudpickle.loads(serialized_function)
        f_remote = ray.remote(**kwargs)(f)
        function_registry[function_id] = f_remote
        print("deployed op: ", function_id)
        print("Available function: ", function_registry.keys())
        return
    
    async def deploy_service(service_id, serialized_service, context=None, **kwargs):
        await server.register_service(
            {
                "name": "Function Launcher",
                "id": "function-launcher",
                "config": {
                    "visibility": "public",
                    "require_context": True,
                    "run_in_executor": True,
                },
                "deploy": deploy_function,
                "run": run_function,
            }
        )

    async def run_function(function_id, *args, context=None, **kwargs):
        f_remote = function_registry[function_id]
        print("running op: ", function_id)
        result = await f_remote.remote(*args, **kwargs)
        print("op finished: ", function_id)
        return result

    await server.register_service(
        {
            "name": "Function Launcher",
            "id": "function-launcher",
            "config": {
                "visibility": "public",
                "require_context": True,
                "run_in_executor": True,
            },
            "deploy": deploy_function,
            "run": run_function,
        }
    )
    print("Function Launcher is ready to receive request!")
    # print("workspace: ", server.config['workspace'], "\ntoken:", await server.generate_token())


async def start_function_launcher(server_url, workspace, token, ray_address):
    server = await connect_to_server(
        {
            "name": "function client",
            "server_url": server_url,
            "token": token,
            "workspace": workspace,
        }
    )
    await register_function_launcher(server, ray_address=ray_address)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-url", default="https://ai.imjoy.io")
    parser.add_argument("--workspace", default=None)
    parser.add_argument("--token", default=None)
    parser.add_argument("--ray-server", default="auto")
    opts = parser.parse_args()

    loop = asyncio.get_event_loop()
    task = loop.create_task(
        start_function_launcher(
            ray_address=opts.ray_server,
            server_url=opts.server_url,
            token=opts.token,
            workspace=opts.workspace,
        )
    )
    loop.run_forever()
