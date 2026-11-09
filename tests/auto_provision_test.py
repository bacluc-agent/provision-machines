from pathlib import Path

_DEPLOY = Path(__file__).parents[1] / "deploys" / "auto_provision"


def test_runner_uses_the_provisioned_uv_binary() -> None:
    runner = (_DEPLOY / "files" / "auto-provision-runner.sh.j2").read_text()

    assert "run_as_user sh -c 'cd \"$1\" && uv run scripts/run_pyinfra_local.py'" in runner
    assert 'trap finish EXIT' in runner
    assert 'trap stop_today TERM INT' in runner


def test_notification_stop_command_records_today_as_stopped() -> None:
    notifier = (_DEPLOY / "files" / "auto-provision-notify.sh.j2").read_text()
    deploy = (_DEPLOY / "deploy.py").read_text()

    assert "Run sudo auto-provision-stop" in notifier
    assert 'state_dir = auto_provision["state_dir"].format(user=user)' in deploy

    stop_script = (_DEPLOY / "files" / "auto-provision-stop.sh.j2").read_text()
    assert "systemctl stop auto-provision.service" in stop_script
    assert 'date +%F > "$STATE_DIR/stopped-today"' in stop_script


def test_disabling_auto_provision_removes_all_units() -> None:
    deploy = (_DEPLOY / "deploy.py").read_text()

    assert "else:\n    for service in (" in deploy
    for service in (
        "auto-provision.timer",
        "auto-provision-notify.timer",
        "auto-provision.service",
        "auto-provision-notify.service",
    ):
        assert f'        "{service}",' in deploy
        assert '            path=f"/etc/systemd/system/{service}"' in deploy


def test_notification_is_configured_two_hours_before_provisioning() -> None:
    deploy = (_DEPLOY / "deploy.py").read_text()

    assert "timedelta(hours=2)" in "".join(deploy.split())
    assert 'auto_provision["notify_on_calendar"]' in deploy


def test_templates_render_all_four_units() -> None:
    deploy = (_DEPLOY / "deploy.py").read_text()

    assert deploy.count('files.template(') == 7
    assert (_DEPLOY / "files" / "auto-provision.service.j2").read_text().count("StandardOutput=journal") == 1
    assert (_DEPLOY / "files" / "auto-provision.timer.j2").read_text().count("OnCalendar=") == 1
