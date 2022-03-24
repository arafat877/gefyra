from gefyra import lazy

logging = lazy("logging")
time = lazy("time")

docker = lazy("docker")
gefyra = lazy("gefyra")

logger = logging.getLogger(__name__)


def handle_create_interceptrequest(
    config: gefyra.configuration.ClientConfiguration, body
):
    ireq = config.K8S_CUSTOM_OBJECT_API.create_namespaced_custom_object(
        namespace=config.NAMESPACE,
        body=body,
        group="gefyra.dev",
        plural="interceptrequests",
        version="v1",
    )
    return ireq


def handle_delete_interceptrequest(
    config: gefyra.configuration.ClientConfiguration, name: str
) -> bool:
    from kubernetes.client import ApiException

    try:
        ireq = config.K8S_CUSTOM_OBJECT_API.delete_namespaced_custom_object(
            namespace=config.NAMESPACE,
            name=name,
            group="gefyra.dev",
            plural="interceptrequests",
            version="v1",
        )
        gefyra.local.cargo.delete_syncdown_job(config, ireq["metadata"]["name"])
        return True
    except ApiException as e:
        if e.status == 404:
            logger.debug(f"InterceptRequest {name} not found")
        else:
            logger.debug("Error removing InterceptRequest: " + str(e))
        return False


def get_all_interceptrequests(config: gefyra.configuration.ClientConfiguration) -> list:
    from kubernetes.client import ApiException

    try:
        ireq_list = config.K8S_CUSTOM_OBJECT_API.list_namespaced_custom_object(
            namespace=config.NAMESPACE,
            group="gefyra.dev",
            plural="interceptrequests",
            version="v1",
        )
        if ireq_list:
            return list(ireq_list.get("items"))
        else:
            return []
    except ApiException as e:
        logger.error("Error getting InterceptRequests: " + str(e))


def remove_interceptrequest_remainder(config: gefyra.configuration.ClientConfiguration):
    from kubernetes.client import ApiException

    try:
        ireq_list = get_all_interceptrequests(config)
        if ireq_list:
            logger.debug(f"Removing {len(ireq_list)} InterceptRequests remainder")
            # if there are running intercept requests clean them up
            for ireq in ireq_list:
                handle_delete_interceptrequest(config, ireq["metadata"]["name"])
                time.sleep(1)
    except ApiException as e:
        logger.error("Error removing remainder InterceptRequests: " + str(e))


def get_ireq_body(
    config: gefyra.configuration.ClientConfiguration,
    name: str,
    destination_ip,
    target_pod,
    target_namespace,
    target_container,
    port_mappings,
    sync_down_directories,
    handle_probes,
):
    return {
        "apiVersion": "gefyra.dev/v1",
        "kind": "InterceptRequest",
        "metadata": {
            "name": name,
            "namspace": config.NAMESPACE,
        },
        "destinationIP": destination_ip,
        "targetPod": target_pod,
        "targetNamespace": target_namespace,
        "targetContainer": target_container,
        "portMappings": port_mappings,
        "syncDownDirectories": sync_down_directories,
        "handleProbes": handle_probes,
    }


def deploy_app_container(
    config: gefyra.configuration.ClientConfiguration,
    image: str,
    name: str = None,
    command: str = None,
    volumes: dict = None,
    ports: dict = None,
    env: dict = None,
    auto_remove: bool = None,
    dns_search: str = "default",
) -> docker.models.containers.Container:

    gefyra_net = config.DOCKER.networks.get(config.NETWORK_NAME)

    net_add = gefyra_net.attrs["IPAM"]["Config"][0]["Subnet"].split("/")[0]
    cargo_ip = gefyra.local.cargo.get_cargo_ip_from_netaddress(net_add)
    all_kwargs = {
        "network": config.NETWORK_NAME,
        "name": name,
        "command": command,
        "volumes": volumes,
        "ports": ports,
        "detach": True,
        "dns": [config.STOWAWAY_IP],
        "dns_search": [dns_search],
        "auto_remove": auto_remove,
        "environment": env,
        "pid_mode": "container:gefyra-cargo",
    }
    not_none_kwargs = {k: v for k, v in all_kwargs.items() if v is not None}

    container = gefyra.local.utils.handle_docker_run_container(
        config, image, **not_none_kwargs
    )

    cargo = config.DOCKER.containers.get(config.CARGO_CONTAINER_NAME)
    exit_code, output = cargo.exec_run(
        f"bash patchContainerGateway.sh {container.name} {cargo_ip}"
    )
    if exit_code == 0:
        logger.debug(f"Gateway patch applied to '{container.name}'")

    else:
        logger.error(
            f"Gateway patch could not be applied to '{container.name}': {output}"
        )
    return container
