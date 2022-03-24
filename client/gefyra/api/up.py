from gefyra import lazy

logging = lazy("logging")
json = lazy("json")

kubernetes = lazy("kubernetes")
docker = lazy("docker")

gefyra = lazy("gefyra")

logger = logging.getLogger(__name__)


def up(
    cargo_endpoint: str = None, config=gefyra.configuration.default_configuration
) -> bool:
    if cargo_endpoint:
        config.CARGO_ENDPOINT = cargo_endpoint
    logger.info("Installing Gefyra Operator")
    #
    # Deploy Operator to cluster, aligned with local conditions
    #
    try:
        network_address = gefyra.local.networking.get_free_class_c_netaddress(config)
        cargo_connection_details = gefyra.cluster.manager.install_operator(
            config, network_address
        )
    except kubernetes.client.ApiException as e:
        data = json.loads(e.body)
        try:
            logger.error(f"{e.reason}: {data['details']['causes'][0]['message']}")
        except KeyError:
            logger.error(f"{e.reason}: {data}")

        return False
    #
    # Run up a local Docker network setup
    #
    try:
        cargo_com_net_ip_address = cargo_connection_details["Interface.Address"]
        stowaway_ip_address = cargo_connection_details["Interface.DNS"].split(" ")[0]
        logger.debug(f"Cargo com net ip address: {cargo_com_net_ip_address}")
        logger.debug(f"Stowaway com net ip address: {stowaway_ip_address}")
        logger.info("Creating Docker network")
        gefyra_network = gefyra.local.networking.handle_create_network(
            config, network_address, {}
        )
        # well known cargo address
        logger.debug(gefyra_network.attrs)
        cargo_ip_address = gefyra.local.cargo.get_cargo_ip_from_netaddress(
            gefyra_network.attrs["IPAM"]["Config"][0]["Subnet"]
        )
        logger.info(f"Deploying Cargo (network sidecar) with IP {cargo_ip_address}")
    except Exception as e:
        logger.error(e)
        gefyra.api.down(config)
        return False
    #
    # Connect Docker network with K8s cluster
    #
    try:
        cargo_container = gefyra.local.cargo.create_cargo_container(
            config, cargo_connection_details
        )
        logger.debug(f"Cargo gefyra net ip address: {cargo_ip_address}")
        gefyra_network.connect(cargo_container, ipv4_address=cargo_ip_address)
        cargo_container.start()
    except docker.errors.APIError as e:
        if e.status_code == 409:
            logger.warning("Cargo is already deployed and running")
        else:
            raise e
    return True
