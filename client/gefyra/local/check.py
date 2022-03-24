from gefyra import lazy

logging = lazy("logging")

gefyra = lazy("gefyra")

logger = logging.getLogger("gefyra")


def probe_docker(
    config: gefyra.configuration.ClientConfiguration = gefyra.configuration.default_configuration,
):
    logger.debug("Probing: Docker")
    try:
        config.DOCKER.containers.list()
        config.DOCKER.images.pull("quay.io/gefyra/cargo:latest")
    except Exception:
        logger.error("Docker does not seem to be not working for Gefyra")
    else:
        logger.info("Docker: Ok")


def probe_kubernetes(
    config: gefyra.configuration.ClientConfiguration = gefyra.configuration.default_configuration,
):
    logger.debug("Probing: Kubernetes")
    try:
        config.K8S_CORE_API.list_namespace()
    except Exception:
        logger.error(
            "Kubernetes is not connected to a cluster or does not seem to be working for Gefyra"
        )
    else:
        logger.info("Kubernetes: Ok")
