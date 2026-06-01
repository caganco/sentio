"""
DataHub unit testleri — network/DB cagri yok, mock fetcher kullanilir.
"""
from __future__ import annotations

import pytest

from src.data.data_hub import DataHub, DataSource


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_hub():
    """Her test oncesi registry temizle (test izolasyonu)."""
    DataHub._reset()
    yield
    DataHub._reset()


def _mock_source(name: str, return_value=None, fallback=None) -> DataSource:
    def fetcher(**kwargs):
        if return_value is Exception:
            raise RuntimeError(f"mock hata: {name}")
        return return_value or {"source": name, "kwargs": kwargs}

    return DataSource(
        name=name,
        description=f"Mock kaynak: {name}",
        data_type="test",
        fetcher=fetcher,
        fallback=fallback,
        auth_required=False,
        tags=["test"],
    )


def _failing_source(name: str, fallback=None) -> DataSource:
    def fetcher(**kwargs):
        raise RuntimeError(f"kaynak hata: {name}")

    return DataSource(
        name=name,
        description=f"Hata veren kaynak: {name}",
        data_type="test",
        fetcher=fetcher,
        fallback=fallback,
        auth_required=False,
        tags=["test"],
    )


# ---------------------------------------------------------------------------
# Kayit testleri
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_register_adds_source(self):
        DataHub._bootstrapped = True  # bootstrap'i atla
        DataHub.register(_mock_source("test_a"))
        assert "test_a" in DataHub.source_names()

    def test_register_overwrites_existing(self):
        DataHub._bootstrapped = True
        DataHub.register(_mock_source("dup", return_value={"v": 1}))
        DataHub.register(_mock_source("dup", return_value={"v": 2}))
        result = DataHub.get("dup")
        assert result["v"] == 2

    def test_list_sources_structure(self):
        DataHub._bootstrapped = True
        DataHub.register(_mock_source("src_x"))
        sources = DataHub.list_sources()
        assert len(sources) == 1
        src = sources[0]
        for key in ("name", "description", "data_type", "auth_required", "fallback", "tags"):
            assert key in src

    def test_source_names_returns_list(self):
        DataHub._bootstrapped = True
        DataHub.register(_mock_source("a"))
        DataHub.register(_mock_source("b"))
        names = DataHub.source_names()
        assert set(names) == {"a", "b"}


# ---------------------------------------------------------------------------
# get() testleri
# ---------------------------------------------------------------------------


class TestGet:
    def test_get_calls_fetcher_and_returns(self):
        DataHub._bootstrapped = True
        DataHub.register(_mock_source("price", return_value={"close": 100.0}))
        result = DataHub.get("price")
        assert result == {"close": 100.0}

    def test_get_passes_kwargs_to_fetcher(self):
        DataHub._bootstrapped = True

        received = {}

        def fetcher(**kwargs):
            received.update(kwargs)
            return {}

        DataHub.register(
            DataSource(name="kw_test", description="", data_type="test", fetcher=fetcher)
        )
        DataHub.get("kw_test", ticker="AKBNK", lookback="6mo")
        assert received["ticker"] == "AKBNK"
        assert received["lookback"] == "6mo"

    def test_get_unknown_source_raises_key_error(self):
        DataHub._bootstrapped = True
        with pytest.raises(KeyError, match="kayitli degil"):
            DataHub.get("nonexistent_xyz")

    def test_get_with_fallback_on_failure(self):
        DataHub._bootstrapped = True
        DataHub.register(_failing_source("primary", fallback="backup"))
        DataHub.register(_mock_source("backup", return_value={"from": "backup"}))

        result = DataHub.get("primary")
        assert result["from"] == "backup"

    def test_get_raises_if_both_primary_and_fallback_fail(self):
        DataHub._bootstrapped = True
        DataHub.register(_failing_source("primary", fallback="also_failing"))
        DataHub.register(_failing_source("also_failing", fallback=None))

        with pytest.raises(RuntimeError):
            DataHub.get("primary")

    def test_get_no_fallback_raises_on_failure(self):
        DataHub._bootstrapped = True
        DataHub.register(_failing_source("lone", fallback=None))

        with pytest.raises(RuntimeError, match="kaynak hata"):
            DataHub.get("lone")


# ---------------------------------------------------------------------------
# Fallback zinciri testleri
# ---------------------------------------------------------------------------


class TestFallbackChain:
    def test_three_level_fallback_resolves_last(self):
        DataHub._bootstrapped = True
        DataHub.register(_failing_source("l1", fallback="l2"))
        DataHub.register(_failing_source("l2", fallback="l3"))
        DataHub.register(_mock_source("l3", return_value={"level": 3}))

        result = DataHub.get("l1")
        assert result["level"] == 3

    def test_fallback_receives_same_kwargs(self):
        DataHub._bootstrapped = True
        received = {}

        def backup_fetcher(**kwargs):
            received.update(kwargs)
            return {}

        DataHub.register(_failing_source("main", fallback="backup"))
        DataHub.register(
            DataSource(
                name="backup",
                description="",
                data_type="test",
                fetcher=backup_fetcher,
            )
        )
        DataHub.get("main", ticker="EREGL", lookback="3mo")
        assert received["ticker"] == "EREGL"


# ---------------------------------------------------------------------------
# Mimari testleri
# ---------------------------------------------------------------------------


class TestArchitecture:
    def test_data_hub_does_not_import_engine(self):
        """data_hub.py engine.py import etmemeli."""
        import ast
        import pathlib

        src = pathlib.Path("src/data/data_hub.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = (
                    [alias.name for alias in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or ""]
                )
                for name in names:
                    assert "engine" not in (name or ""), (
                        f"data_hub.py engine import ediyor: {name}"
                    )

    def test_hub_sources_no_toplevel_engine_import(self):
        """_hub_sources.py modul seviyesinde engine import etmemeli."""
        import ast
        import pathlib

        src = pathlib.Path("src/data/_hub_sources.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = (
                    [alias.name for alias in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or ""]
                )
                for name in names:
                    assert "engine" not in (name or ""), (
                        f"_hub_sources.py modul seviyesinde engine import ediyor: {name}"
                    )

    def test_data_source_has_required_fields(self):
        DataHub._bootstrapped = True
        src = _mock_source("field_test")
        DataHub.register(src)
        listed = DataHub.list_sources()[0]
        assert listed["name"] == "field_test"
        assert isinstance(listed["tags"], list)
        assert isinstance(listed["auth_required"], bool)
