"""Tests for ingest.env_loader — robust .env parsing per Gemini MED r1."""

from __future__ import annotations

import pytest

from ingest.env_loader import load_env


def test_basic_keyvalue(tmp_path):
    f = tmp_path / ".env"
    f.write_text("KEY=value\nFOO=bar baz\n", encoding="utf-8")
    d = load_env(f)
    assert d == {"KEY": "value", "FOO": "bar baz"}


def test_ignores_whole_line_comments(tmp_path):
    f = tmp_path / ".env"
    f.write_text("# comment\nKEY=value\n# another\n", encoding="utf-8")
    assert load_env(f) == {"KEY": "value"}


def test_strips_inline_comment(tmp_path):
    f = tmp_path / ".env"
    f.write_text("KEY=value # inline comment\nOTHER=x\n", encoding="utf-8")
    d = load_env(f)
    assert d["KEY"] == "value"
    assert d["OTHER"] == "x"


def test_preserves_hash_without_whitespace(tmp_path):
    f = tmp_path / ".env"
    f.write_text("URL=http://foo/bar#anchor\n", encoding="utf-8")
    assert load_env(f)["URL"] == "http://foo/bar#anchor"


def test_strips_double_quotes(tmp_path):
    f = tmp_path / ".env"
    f.write_text('KEY="value with spaces"\n', encoding="utf-8")
    assert load_env(f)["KEY"] == "value with spaces"


def test_strips_single_quotes(tmp_path):
    f = tmp_path / ".env"
    f.write_text("KEY='quoted value'\n", encoding="utf-8")
    assert load_env(f)["KEY"] == "quoted value"


def test_hash_inside_quotes_preserved(tmp_path):
    f = tmp_path / ".env"
    f.write_text('KEY="value # with hash"\n', encoding="utf-8")
    assert load_env(f)["KEY"] == "value # with hash"


def test_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_env(tmp_path / "nonexistent.env")


def test_empty_lines_skipped(tmp_path):
    f = tmp_path / ".env"
    f.write_text("\n\nKEY=value\n\n", encoding="utf-8")
    assert load_env(f) == {"KEY": "value"}


def test_lines_without_equals_skipped(tmp_path):
    f = tmp_path / ".env"
    f.write_text("no equals here\nKEY=value\n", encoding="utf-8")
    assert load_env(f) == {"KEY": "value"}
