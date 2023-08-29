import docker
import random
import string

DOCKER_CONTAINER_PREFIX = "hypha-container-launcher-"


def run_container(
    client: any,
    image: str,
    command: str,
    cpu_count: int = None,
    gpu_count: int = None,
    name: str = None,
    working_dir: str = None,
    environment=None,
    detach=False,
    shm_size="64M",
    ulimits=None,
    labels=None,
):
    """Launch a docker container."""

    # Generate a random suffix for the container name
    suffix = name or "".join(
        random.choices(string.ascii_lowercase + string.digits, k=24)
    )
    container_name = f"{DOCKER_CONTAINER_PREFIX}{suffix}"

    assert name != "all", "Container name cannot be 'all'"

    # Check if the container already exists
    if exists_container(client, suffix):
        raise RuntimeError(f"Container {suffix} already exists")

    ret = client.containers.run(
        image,
        command,
        detach=detach,
        name=container_name,
        cpu_count=cpu_count,
        device_requests=[
            {"driver": "nvidia", "count": gpu_count, "capabilities": [["gpu"]]}
        ]
        if gpu_count
        else None,
        working_dir=working_dir,
        environment=environment,
        shm_size=shm_size,
        ulimits=ulimits,
        labels=labels,
    )
    if detach:
        assert ret.status in ["created", "running", "removing", "exited", "dead"], (
            "Failed to create the container, invalid status: " + ret.status
        )
        return suffix
    else:
        return ret.decode("utf-8")


def exists_container(client: any, name: str) -> bool:
    container_name = f"{DOCKER_CONTAINER_PREFIX}{name}"

    # Check if the container already exists
    try:
        client.containers.get(container_name)
        return True
    except docker.errors.NotFound:
        return False


def status_container(client: any, name: str) -> bool:
    container_name = f"{DOCKER_CONTAINER_PREFIX}{name}"
    container = client.containers.get(container_name)
    return container.status


def logs_container(client: any, container_name: str) -> str:
    """Fetch the logs of a docker container."""
    try:
        container = client.containers.get(f"{DOCKER_CONTAINER_PREFIX}{container_name}")
        logs = container.logs()
        return logs.decode("utf-8")
    except docker.errors.NotFound:
        raise Exception(f"Container {container_name} does not exist")


def list_containers(client: any) -> list:
    """List the names of all docker containers."""

    # Fetch all containers
    containers = client.containers.list(all=True)

    # Filter containers whose names start with errors
    matching_containers = [
        container.name[len(DOCKER_CONTAINER_PREFIX) :]
        for container in containers
        if container.name.startswith(DOCKER_CONTAINER_PREFIX)
    ]
    return matching_containers


def stop_container(client: any, name: str):
    """Stop a docker container or all containers."""

    if name == "all":
        containers = client.containers.list(all=True)
        matching_containers = [
            container
            for container in containers
            if container.name.startswith(DOCKER_CONTAINER_PREFIX)
        ]

        for container in matching_containers:
            container.stop()
            container.remove()
    else:
        try:
            container = client.containers.get(f"{DOCKER_CONTAINER_PREFIX}{name}")
            if container.status == "running":
                container.stop()
            container.remove()
        except docker.errors.NotFound:
            raise Exception(f"Container {name} does not exist")


def run_container_tests(client: any):
    if exists_container(client, "test"):
        stop_container(client, "test")
    image: str = "alpine"
    command: str = "echo hello"

    stop_container(client, "all")

    # Test run_container function
    print("Running test container...")
    ret = run_container(client, image, command, name="test", detach=False)
    assert ret == "hello\n", "Failed to run the container"

    print("Test container running.")

    # stop_container(client, 'test')
    # run_container(client, image, command, name='test', detach=True)

    # Test logs_container function
    print("Fetching logs...")
    logs = logs_container(client, "test")
    assert "hello" in logs, "Unexpected logs output: " + logs
    print("Logs fetched.")

    # Test list_containers function
    print("Listing containers...")
    container_list = list_containers(client)

    assert any("test" in s for s in container_list), "Failed to list the test container"
    print("Containers listed.")

    # Test stop_container function
    print("Stopping test container...")
    stop_container(client, "test")
    assert not exists_container(client, "test"), "Failed to stop the container"
    print("Test container stopped.")

    print("Finished running docker tests.")


if __name__ == "__main__":
    client = docker.from_env()
    run_container_tests(client)
