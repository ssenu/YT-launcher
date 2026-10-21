from yt_launcher.geometry import Rect, default_rect, is_visible_on_any


def test_default_rect_top_right_of_primary():
    assert default_rect(Rect(0, 0, 1920, 1040)) == Rect(1544, 16, 360, 480)


def test_default_rect_respects_work_area_offset():
    assert default_rect(Rect(1920, 0, 1280, 984)) == Rect(2824, 16, 360, 480)


def test_default_rect_shrinks_on_small_screens():
    assert default_rect(Rect(0, 0, 300, 400)) == Rect(16, 16, 268, 368)


def test_intersection_area():
    assert Rect(0, 0, 100, 100).intersection_area(Rect(50, 50, 100, 100)) == 2500
    assert Rect(0, 0, 100, 100).intersection_area(Rect(200, 0, 10, 10)) == 0


def test_visible_when_mostly_on_screen():
    works = [Rect(0, 0, 1920, 1080)]
    assert is_visible_on_any(Rect(100, 100, 360, 480), works)
    assert is_visible_on_any(Rect(1800, 0, 200, 100), works)  # 60% 겹침


def test_not_visible_when_off_screen_or_barely_overlapping():
    works = [Rect(0, 0, 1920, 1080)]
    assert not is_visible_on_any(Rect(5000, 0, 360, 480), works)
    assert not is_visible_on_any(Rect(1880, 0, 200, 100), works)  # 20% 겹침
    assert not is_visible_on_any(Rect(0, 0, 0, 0), works)


def test_visible_on_secondary_monitor():
    works = [Rect(0, 0, 1920, 1080), Rect(1920, 0, 1280, 1024)]
    assert is_visible_on_any(Rect(2500, 100, 360, 480), works)