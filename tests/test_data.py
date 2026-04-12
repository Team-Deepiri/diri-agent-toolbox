import pytest

from diri_agent_toolbox.data import safe_calculate


@pytest.mark.parametrize(
    "expr,expected",
    [
        ("2 + 2", 4),
        ("sqrt(16)", 4.0),
        ("pow(2, 3)", 8),
        ("pi", pytest.approx(3.14159, rel=1e-4)),
    ],
)
def test_safe_calculate(expr, expected):
    assert safe_calculate(expr) == expected


def test_safe_calculate_rejects_bad_syntax():
    with pytest.raises(ValueError):
        safe_calculate("__import__('os')")


@pytest.mark.asyncio
async def test_calculate_tool():
    from diri_agent_toolbox.data import calculate

    r = await calculate("3 * 4 + 1")
    assert r.success and r.result == 13


@pytest.mark.asyncio
async def test_json_roundtrip():
    from diri_agent_toolbox.data import json_format, json_parse

    p = await json_parse('{"a": 1}')
    assert p.success
    f = await json_format(p.result)
    assert f.success and '"a"' in (f.result or "")
