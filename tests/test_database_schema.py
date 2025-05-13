import pytest


def test_schema_import():
    """測試資料庫 schema 模組能否正確匯入。"""
    import src.database.schema
    assert hasattr(src.database.schema, "__file__") 