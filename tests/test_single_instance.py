import uuid

from yt_launcher.single_instance import SingleInstance


def test_second_instance_signals_first(qapp):
    name = f"YTLauncherTest-{uuid.uuid4().hex}"
    first = SingleInstance(name)
    assert first.acquire() is True
    activated = []
    first.activated.connect(lambda: activated.append(True))

    second = SingleInstance(name)
    assert second.acquire() is False

    for _ in range(50):
        qapp.processEvents()
        if activated:
            break
    assert activated == [True]


def test_notify_existing_reports_connection(qapp):
    name = f"YTLauncherTest-{uuid.uuid4().hex}"
    assert SingleInstance(name).notify_existing() is False
    first = SingleInstance(name)
    assert first.acquire() is True
    activated = []
    first.activated.connect(lambda: activated.append(True))
    assert SingleInstance(name).notify_existing() is True
    for _ in range(50):
        qapp.processEvents()
        if activated:
            break
    assert activated == [True]