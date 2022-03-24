from gefyra import lazy

logging = lazy("logging")
typing = lazy("typing")

gefyra = lazy("gefyra")

from .utils import stopwatch  # noqa


logger = logging.getLogger(__name__)


@stopwatch
def list_interceptrequests(
    config=gefyra.configuration.default_configuration,
) -> typing.List[str]:
    from gefyra.local.bridge import get_all_interceptrequests

    ireqs = []
    for ireq in get_all_interceptrequests(config):
        ireqs.append(ireq["metadata"]["name"])
    return ireqs
