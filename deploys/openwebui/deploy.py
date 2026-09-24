import io
import json

from pyinfra import host
from pyinfra.facts.files import Directory
from pyinfra.operations import files, server, systemd

from deploys.openwebui.render import reconciliation_command, render_compose, render_env, render_manifest
from operations.filesystem import dirname_of
from operations.user import get_user_name

# renovate: datasource=docker depName=ghcr.io/api7/aisix
AISIX_VERSION = "1.4.0"


def deploy_openwebui(openwebui: dict[str, object], user: str) -> None:
    compose_project_dir = str(openwebui.get("compose_project_dir") or f"/home/{user}/openwebui")
    deploy_dir = dirname_of(__file__)

    server.shell(
        name="Create docker volume",
        commands=["docker volume create open-webui"],
        _sudo=True,
        _if=lambda: host.get_fact(Directory, "/var/lib/docker/volumes/open-webui") is None,
    )

    compose_directory = files.directory(
        name="Create compose project directory",
        path=compose_project_dir,
        user=user,
        group=user,
        mode="755",
    )

    searxng_files = files.sync(
        name="Copy searngx directory",
        src=f"{deploy_dir}/files/searngx",
        dest=f"{compose_project_dir}/searngx",
        mode="755",
        exclude="*/settings.yml",
    )

    with open(f"{deploy_dir}/files/searngx/settings.yml") as settings_template:
        settings = settings_template.read().replace(
            '"${BRAVE_API_KEY}"', json.dumps(str(openwebui.get("BRAVE_API_KEY", "")))
        )

    settings_file = files.put(
        name="Deploy searxng settings.yml",
        src=io.StringIO(settings),
        dest=f"{compose_project_dir}/searngx/settings.yml",
        user=user,
        group=user,
        mode="600",
        _sudo=True,
    )

    compose_file = files.put(
        name="Deploy docker-compose.yml",
        src=io.StringIO(render_compose(f"{deploy_dir}/files/docker-compose.yml", AISIX_VERSION)),
        dest=f"{compose_project_dir}/docker-compose.yml",
        user=user,
        group=user,
        mode="644",
    )

    env_file = files.put(
        name="Deploy .env",
        src=io.StringIO(render_env(openwebui, AISIX_VERSION)),
        dest=f"{compose_project_dir}/.env",
        user=user,
        group=user,
        mode="600",
        _sudo=True,
    )

    aisix_config_file = files.put(
        name="Deploy aisix-config.yaml",
        src=f"{deploy_dir}/files/aisix-config.yaml",
        dest=f"{compose_project_dir}/aisix-config.yaml",
        user=user,
        group=user,
        mode="644",
    )

    aisix_resources_file = files.put(
        name="Deploy aisix-resources.yaml",
        src=f"{deploy_dir}/files/aisix-resources.yaml",
        dest=f"{compose_project_dir}/aisix-resources.yaml",
        user=user,
        group=user,
        mode="644",
    )

    models_manifest_file = files.put(
        name="Deploy openwebui-models.json",
        src=io.StringIO(render_manifest(openwebui)),
        dest=f"{compose_project_dir}/openwebui-models.json",
        user=user,
        group=user,
        mode="644",
    )

    reconciler_file = files.put(
        name="Deploy update-openwebui-models.py",
        src=f"{deploy_dir}/../../scripts/update-openwebui-models.py",
        dest=f"{compose_project_dir}/update-openwebui-models.py",
        user=user,
        group=user,
        mode="755",
    )

    systemd_file = files.put(
        name="Deploy systemd service file",
        src=io.StringIO(
            f"""[Unit]
Description=OpenWebUI Service
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory={compose_project_dir}
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
"""
        ),
        dest="/etc/systemd/system/openwebui.service",
        _sudo=True,
        mode="644",
    )

    changed_files = (
        compose_directory,
        searxng_files,
        settings_file,
        compose_file,
        env_file,
        aisix_config_file,
        aisix_resources_file,
        models_manifest_file,
        reconciler_file,
        systemd_file,
    )

    def files_changed() -> bool:
        return any(file.changed for file in changed_files)

    server.shell(
        name="Restart docker before starting openwebui to ensure iptables chains exist",
        commands=["systemctl restart docker"],
        _sudo=True,
        _if=files_changed,
    )

    systemd.service(
        name="Enable and start openwebui service",
        service="openwebui",
        daemon_reload=True,
        enabled=True,
        restarted=True,
        _sudo=True,
        _if=files_changed,
    )

    server.shell(
        name="Reconcile OpenWebUI models",
        commands=[reconciliation_command(compose_project_dir)],
        _sudo=True,
    )


data = getattr(host, "data", None)
if data is not None and data.get("openwebui", {}).get("enabled", False):
    deploy_openwebui(data.openwebui, get_user_name())
