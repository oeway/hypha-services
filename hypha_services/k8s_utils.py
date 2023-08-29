import random
import string
from kubernetes import config, client
from kubernetes.client.models import (
    V1Pod,
    V1ObjectMeta,
    V1PodSpec,
    V1Container,
    V1ResourceRequirements,
)

K8S_POD_PREFIX = "hypha-container-launcher-"
NAMESPACE = "default"  # global namespace variable


def run_container(
    client_api,
    image: str,
    command: str,
    cpu_count: int = None,
    gpu_count: int = None,
    name: str = None,
    environment=None,
    detach=False,
    shm_size="64M",
    ulimits=None,
    labels=None,
):
    # Generate a random suffix for the pod name
    suffix = name or "".join(
        random.choices(string.ascii_lowercase + string.digits, k=24)
    )
    pod_name = f"{K8S_POD_PREFIX}{suffix}"

    pod = V1Pod(
        metadata=V1ObjectMeta(name=pod_name),
        spec=V1PodSpec(
            containers=[
                V1Container(
                    name=pod_name,
                    image=image,
                    command=command.split(" "),
                    resources=V1ResourceRequirements(
                        limits={"cpu": cpu_count, "nvidia.com/gpu": gpu_count}
                        if cpu_count or gpu_count
                        else None
                    ),
                )
            ]
        ),
    )
    client_api.create_namespaced_pod(namespace=NAMESPACE, body=pod)
    return suffix


def exists_container(client_api, name: str) -> bool:
    pod_name = f"{K8S_POD_PREFIX}{name}"
    try:
        client_api.read_namespaced_pod(name=pod_name, namespace=NAMESPACE)
        return True
    except client.exceptions.ApiException as e:
        if e.status == 404:
            return False
        else:
            raise


def logs_container(client_api, name: str) -> str:
    pod_name = f"{K8S_POD_PREFIX}{name}"
    try:
        logs = client_api.read_namespaced_pod_log(name=pod_name, namespace=NAMESPACE)
        return logs
    except client.exceptions.ApiException as e:
        if e.status == 404:
            raise Exception(f"Pod {name} does not exist")
        else:
            raise


def list_containers(client_api) -> list:
    pods = client_api.list_namespaced_pod(namespace=NAMESPACE)
    matching_pods = [
        pod.metadata.name[len(K8S_POD_PREFIX) :]
        for pod in pods.items
        if pod.metadata.name.startswith(K8S_POD_PREFIX)
    ]
    return matching_pods


def stop_container(client_api, name: str):
    if name == "all":
        pods = client_api.list_namespaced_pod(namespace=NAMESPACE)
        matching_pods = [
            pod for pod in pods.items if pod.metadata.name.startswith(K8S_POD_PREFIX)
        ]

        for pod in matching_pods:
            client_api.delete_namespaced_pod(
                name=pod.metadata.name, namespace=NAMESPACE, grace_period_seconds=0
            )
    else:
        pod_name = f"{K8S_POD_PREFIX}{name}"
        try:
            client_api.delete_namespaced_pod(
                name=pod_name, namespace=NAMESPACE, grace_period_seconds=0
            )
        except client.exceptions.ApiException as e:
            if e.status == 404:
                raise Exception(f"Pod {name} does not exist")
            else:
                raise


def run_container_tests(client_api: any):
    image = "alpine"
    command = "echo hello"

    # Test run_pod function
    print("Running test pod...")
    if exists_container(client_api, "test"):
        stop_container(client_api, "test")
    run_container(client_api, "test", image, command)
    print("Test pod running.")

    # Test logs_pod function
    print("Fetching logs...")
    logs = logs_container(client_api, "test")
    assert "hello" in logs, "Unexpected logs output: " + logs
    print("Logs fetched.")

    # Test list_pod function
    print("Listing pods...")
    pod_list = list_containers()
    assert any("test" in s for s in pod_list), "Failed to list the test pod"
    print("Pods listed.")

    # Test stop_pod function
    print("Stopping test pod...")
    stop_container(client_api, "test")
    assert not exists_container(client_api, "test"), "Failed to stop the pod"
    print("Test pod stopped.")

    print("Finished running pod tests.")


if __name__ == "__main__":
    config.load_incluster_config()
    client = client.CoreV1Api()
    run_container_tests(client)
