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
        mode="700",
    )

    files.template(
        name="Install auto-provision runner",
        src=f"{dirname_of(__file__)}/files/auto-provision-runner.sh.j2",
        dest="/usr/local/bin/auto-provision-runner",
        _sudo=True,
        mode="755",
        auto_user=user,
        auto_home=f"/home/{user}",
        auto_checkout_dir=checkout_dir,
        auto_branch=auto_provision["branch"],
        auto_state_dir=state_dir,
    )

    files.template(
        name="Install auto-provision notification script",
        src=f"{dirname_of(__file__)}/files/auto-provision-notify.sh.j2",
        dest="/usr/local/bin/auto-provision-notify",
        _sudo=True,
        mode="755",
        auto_user=user,
        auto_state_dir=state_dir,
    )

    files.template(
        name="Install auto-provision service",
        src=f"{dirname_of(__file__)}/files/auto-provision.service.j2",
        dest="/etc/systemd/system/auto-provision.service",
        _sudo=True,
        mode="644",
    )

    files.template(
        name="Install auto-provision timer",
        src=f"{dirname_of(__file__)}/files/auto-provision.timer.j2",
        dest="/etc/systemd/system/auto-provision.timer",
        _sudo=True,
        mode="644",
        auto_on_calendar=auto_provision["on_calendar"],
    )

    files.template(
        name="Install auto-provision notification service",
        src=f"{dirname_of(__file__)}/files/auto-provision-notify.service.j2",
        dest="/etc/systemd/system/auto-provision-notify.service",
        _sudo=True,
        mode="644",
    )

    files.template(
        name="Install auto-provision notification timer",
        src=f"{dirname_of(__file__)}/files/auto-provision-notify.timer.j2",
        dest="/etc/systemd/system/auto-provision-notify.timer",
        _sudo=True,
        mode="644",
        auto_notify_on_calendar=auto_provision["notify_on_calendar"],
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
            daemon_reload=service == "auto-provision.timer",
            _sudo=True,
        )
        files.file(
            name=f"Remove {service}",
            path=f"/etc/systemd/system/{service}",
            present=False,
            _sudo=True,
        )
