import pytest

from sourdough import make_bread


def test_make_bread_hydration():
    r = make_bread(500, 350)
    assert r["flour"] == 500
    assert r["water"] == 350
    assert pytest.approx(r["hydration"]) == 70.0


def test_make_bread_invalid():
    with pytest.raises(ValueError):
        make_bread(0, 100)
