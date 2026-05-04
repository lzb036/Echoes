from echoes.ui.fake_logs import FakeLogService


def test_fake_log_service_limits_lines() -> None:
    logs = FakeLogService(seed=7, max_lines=5)
    for _ in range(20):
        logs.next_line()

    assert len(logs.lines) == 5


def test_fake_log_service_generates_plain_build_output() -> None:
    logs = FakeLogService(seed=1)
    line = logs.next_line()

    assert line
    assert "token" not in line.lower()
