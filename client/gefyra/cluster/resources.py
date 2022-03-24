from gefyra import lazy

logging = lazy("logging")
typing = lazy("typing")

kubernetes = lazy("kubernetes")

gefyra = lazy("gefyra")


logger = logging.getLogger(__name__)


def create_operator_serviceaccount(
    namespace: str,
) -> kubernetes.client.V1ServiceAccount:
    return kubernetes.client.V1ServiceAccount(
        metadata=kubernetes.client.V1ObjectMeta(
            # this name is referenced by Operator
            name="gefyra-operator",
            namespace=namespace,
        )
    )


def create_operator_clusterrole() -> kubernetes.client.V1ClusterRole:
    crd_rule = kubernetes.client.V1PolicyRule(
        api_groups=["apiextensions.k8s.io"],
        resources=["customresourcedefinitions"],
        verbs=["create", "patch", "delete", "list", "watch"],
    )
    kopf_rules = kubernetes.client.V1PolicyRule(
        api_groups=["kopf.dev"],
        resources=["clusterkopfpeerings"],
        verbs=["create", "patch"],
    )
    misc_res_rule = kubernetes.client.V1PolicyRule(
        api_groups=["", "apps", "extensions", "events.k8s.io"],
        resources=[
            "namespaces",
            "configmaps",
            "secrets",
            "deployments",
            "services",
            "pods",
            "pods/exec",
            "events",
        ],
        verbs=["create", "patch", "update", "delete", "get", "list"],
    )
    ireq_rule = kubernetes.client.V1PolicyRule(
        api_groups=["gefyra.dev"], resources=["interceptrequests"], verbs=["*"]
    )

    clusterrole = kubernetes.client.V1ClusterRole(
        kind="ClusterRole",
        metadata=kubernetes.client.V1ObjectMeta(
            # this name is referenced by Operator
            name="gefyra-operator-role",
        ),
        rules=[
            crd_rule,
            kopf_rules,
            # kopf_peering,
            misc_res_rule,
            ireq_rule,
        ],
    )
    return clusterrole


def create_operator_clusterrolebinding(
    serviceaccount: kubernetes.client.V1ServiceAccount,
    clusterrole: kubernetes.client.V1ClusterRole,
    namespace: str,
) -> kubernetes.client.V1ClusterRoleBinding:
    return kubernetes.client.V1ClusterRoleBinding(
        metadata=kubernetes.client.V1ObjectMeta(
            # this name is referenced by Operator
            name="gefyra-operator-rolebinding",
        ),
        role_ref=kubernetes.client.V1RoleRef(
            api_group="rbac.authorization.k8s.io",
            name=clusterrole.metadata.name,
            kind="ClusterRole",
        ),
        subjects=[
            kubernetes.client.V1Subject(
                kind="ServiceAccount",
                name=serviceaccount.metadata.name,
                namespace=namespace,
            )
        ],
    )


def create_operator_deployment(
    serviceaccount: kubernetes.client.V1ServiceAccount,
    namespace: str,
    gefyra_network_subnet: str,
) -> kubernetes.client.V1Deployment:

    template = kubernetes.client.V1PodTemplateSpec(
        metadata=kubernetes.client.V1ObjectMeta(labels={"app": "gefyra-operator"}),
        spec=kubernetes.client.V1PodSpec(
            containers=[
                kubernetes.client.V1Container(
                    name="gefyra-operator",
                    image="quay.io/gefyra/operator:latest",
                    env=[
                        kubernetes.client.V1EnvVar(
                            name="GEFYRA_PEER_SUBNET", value=gefyra_network_subnet
                        )
                    ],
                )
            ],
            service_account_name=serviceaccount.metadata.name,
        ),
    )
    spec = kubernetes.client.V1DeploymentSpec(
        replicas=1,
        template=template,
        selector={"matchLabels": {"app": "gefyra-operator"}},
    )
    deployment = kubernetes.client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=kubernetes.client.V1ObjectMeta(
            name="gefyra-operator", namespace=namespace
        ),
        spec=spec,
    )

    return deployment


def get_pods_for_workload(
    config: gefyra.configuration.ClientConfiguration, name: str, namespace: str
) -> typing.List[str]:
    result = []
    name = name.split("-")
    pods = config.K8S_CORE_API.list_namespaced_pod(namespace)
    for pod in pods.items:
        pod_name = pod.metadata.name.split("-")
        if all(x == y for x, y in zip(name, pod_name)) and len(pod_name) - 2 == len(
            name
        ):
            # this pod name containers all segments of name
            result.append(pod.metadata.name)
    return result
