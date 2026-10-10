"""Check both evaluation destinations against explicitly owned local containers."""

import os
import re
import subprocess
from collections.abc import Callable
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from app.bootstrap.config import Settings


class PublishedPort(BaseModel):
    model_config = ConfigDict(strict=True)
    host_ip: str = Field(alias='HostIp')
    host_port: str = Field(alias='HostPort')


class ContainerNetwork(BaseModel):
    ports: dict[str, list[PublishedPort] | None] = Field(alias='Ports')


class ContainerState(BaseModel):
    model_config = ConfigDict(strict=True)
    running: bool = Field(alias='Running')


class ContainerConfig(BaseModel):
    image: str = Field(alias='Image')
    labels: dict[str, str] | None = Field(alias='Labels')


class EvaluationContainer(BaseModel):
    identity: str = Field(alias='Id')
    config: ContainerConfig = Field(alias='Config')
    state: ContainerState = Field(alias='State')
    network: ContainerNetwork = Field(alias='NetworkSettings')


def inspect_containers(names: tuple[str, str]) -> list[EvaluationContainer]:
    try:
        result = subprocess.run(
            ['docker', 'inspect', '--type', 'container', *names],
            capture_output=True,
            timeout=10,
            check=True,
        )
        return TypeAdapter(list[EvaluationContainer]).validate_json(result.stdout)
    except OSError, subprocess.SubprocessError, ValidationError:
        raise ValueError('cannot verify evaluation container identities') from None


def validate_targets(
    config: Settings,
    *,
    inspect: Callable[
        [tuple[str, str]], list[EvaluationContainer]
    ] = inspect_containers,
) -> None:
    endpoints = (urlparse(config.database_url), urlparse(config.neo4j_uri))
    if config.environment != 'development' or any(
        endpoint.hostname not in ('localhost', '127.0.0.1', '::1')
        for endpoint in endpoints
    ):
        raise ValueError('evaluation requires local development PostgreSQL and Neo4j')
    project = os.environ.get('COMPOSE_PROJECT_NAME', '')
    names = (
        os.environ.get('EVALUATION_POSTGRES_CONTAINER', f'{project}-postgres-1'),
        os.environ.get('EVALUATION_NEO4J_CONTAINER', f'{project}-neo4j-1'),
    )
    if not project and not all(re.fullmatch(r'[a-f0-9]{64}', name) for name in names):
        raise ValueError('declare an isolated Compose project or exact container IDs')
    if any(
        not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}', name) for name in names
    ):
        raise ValueError('invalid evaluation container identifiers')
    containers = inspect(names)
    if len(containers) != 2 or containers[0].identity == containers[1].identity:
        raise ValueError('evaluation requires two distinct owned containers')
    for name, endpoint, container, service, internal_port, images in zip(
        names,
        endpoints,
        containers,
        ('postgres', 'neo4j'),
        (5432, 7687),
        (('postgres:', 'pgvector/pgvector:'), ('neo4j:',)),
        strict=True,
    ):
        labels = container.config.labels or {}
        if re.fullmatch(r'[a-f0-9]{64}', name) and name != container.identity:
            raise ValueError('evaluation container does not match the declared ID')
        if not container.state.running or not container.config.image.startswith(images):
            raise ValueError('evaluation service identity is not an active database')
        if project and (
            labels.get('com.docker.compose.project') != project
            or labels.get('com.docker.compose.service') != service
        ):
            raise ValueError(
                'evaluation service belongs to a different Compose project'
            )
        ports = container.network.ports.get(f'{internal_port}/tcp') or []
        allowed_bindings = {'127.0.0.1', '::1'}
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            allowed_bindings |= {'0.0.0.0', '::'}
        if any(port.host_ip not in allowed_bindings for port in ports) or not any(
            port.host_ip in allowed_bindings
            and port.host_port == str(endpoint.port or internal_port)
            for port in ports
        ):
            raise ValueError('evaluation endpoint does not match its owned container')
