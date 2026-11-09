from datetime import datetime, timedelta

from pyinfra import host
from pyinfra.operations import apt, files, systemd

from operations.filesystem import dirname_of
from operations.user import get_user_name

user = get_user_name()
auto_provision = host.data.auto_provision

execution_day, execution_time = auto_provision["on_calendar"].rsplit(" ", 1)
notification_day, notification_time = auto_provision["notify_on_calendar"].rsplit(" ", 1)
assert execution_day == notification_day
assert datetime.strptime(execution_time, "%H:%M:%S") - datetime.strptime(notification_time, "%H:%M:%S") == timedelta(
    hours=2
)

if auto_provision["enabled"]:
    checkout_dir = auto_provision["checkout_dir"].format(user=user)
    state_dir = auto_provision["state_dir"].format(user=user)
    apt.packages(
        name="Install auto-provision notification dependency",
        packages=["libnotify-bin"],
        update=True,
        _sudo=True,
    )
    files.directory(
        name="Create auto-provision state directory",
        path=state_dir,
        user=user,
        group=user,
        _sudo=True,
        mode="755",
    )

    files.template(
        name="Install auto-provision runner",
        src=f"{dirname_of(__file__)}/files/auto-provision-runner.sh.j2",
        dest="/usr/local/bin/auto-provision-runner",
        _sudo=True,
        mode="755",
        user=user,
        user_name=user,
        home=f"/home/{user}",
        checkout_dir=checkout_dir,
        branch=auto_provision["branch"],
        state_dir=state_dir,
    )

    files.template(
        name="Install auto-provision notification script",
        src=f"{dirname_of(__file__)}/files/auto-provision-notify.sh.j2",
        dest="/usr/local/bin/auto-provision-notify",
        _sudo=True,
        mode="755",
        user_name=user,
        user=user,
        state_dir=state_dir,
    )

    files.template(
        name="Install auto-provision service",
        src=f"{dirname_of(__file__)}/files/auto-provision.service.j2",
        dest="/etc/systemd/system/auto-provision.service",
        _sudo=True,
        mode="644",
        description="Provision the development machine",
        exec_start="/usr/local/bin/auto-provision-runner",
    )

    files.template(
        name="Install auto-provision timer",
        src=f"{dirname_of(__file__)}/files/auto-provision.timer.j2",
        dest="/etc/systemd/system/auto-provision.timer",
        _sudo=True,
        mode="644",
        description="Schedule development machine provisioning",
        on_calendar=auto_provision["on_calendar"],
        persistent="true",
        unit="auto-provision.service",
    )

    files.template(
        name="Install auto-provision notification service",
        src=f"{dirname_of(__file__)}/files/auto-provision.service.j2",
        dest="/etc/systemd/system/auto-provision-notify.service",
        _sudo=True,
        mode="644",
        description="Notify before development machine provisioning",
        exec_start="/usr/local/bin/auto-provision-notify",
    )

    files.template(
        name="Install auto-provision notification timer",
        src=f"{dirname_of(__file__)}/files/auto-provision.timer.j2",
        dest="/etc/systemd/system/auto-provision-notify.timer",
        _sudo=True,
        mode="644",
        description="Schedule the provisioning notification",
        on_calendar=auto_provision["notify_on_calendar"],
        persistent="false",
        unit="auto-provision-notify.service",
    )

    files.template(
        name="Install auto-provision stop command",
        src=f"{dirname_of(__file__)}/files/auto-provision-stop.sh.j2",
        dest="/usr/local/bin/auto-provision-stop",
        _sudo=True,
        mode="755",
        state_dir=state_dir,
    )

    systemd.service(
        name="Enable auto-provision timers",
        service="auto-provision.timer",
        enabled=True,
        daemon_reload=True,
        _sudo=True,
    )
    systemd.service(
        name="Enable auto-provision notification timer",
        service="auto-provision-notify.timer",
        enabled=True,
        daemon_reload=False,
        _sudo=True,
    )
else:
    for service in (
        "auto-provision.timer",
        "auto-provision-notify.timer",
        "auto-provision.service",
        "auto-provision-notify.service",
    ):
        systemd.service(
            name=f"Disable {service}",
            service=service,
            enabled=False,
            running=False,
            daemon_reload=service == "auto-provision-notify.timer",
            _sudo=True,
        )
        files.file(
            name=f"Remove {service}",
            path=f"/etc/systemd/system/{service}",
            present=False,
            _sudo=True,
        )
    files.file(
        name="Remove auto-provision runner",
        path="/usr/local/bin/auto-provision-runner",
        present=False,
        _sudo=True,
    )
    files.file(
        name="Remove auto-provision notifier",
        path="/usr/local/bin/auto-provision-notify",
        present=False,
        _sudo=True,
    )
    files.file(
        name="Remove auto-provision stop command",
        path="/usr/local/bin/auto-provision-stop",
        present=False,
        _sudo=True,
    )
