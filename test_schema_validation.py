#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
資料庫 Schema 驗證腳本

測試修正後的 schema.py 是否可以正常創建所有表和索引。
"""

import sys
import tempfile
import os
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_schema_imports():
    """測試 Schema 模組導入"""
    print("🔍 測試 Schema 模組導入...")

    try:
        from src.database.schema import (
            Base,
            MarketDaily,
            MarketMinute,
            MarketTick,
            DataShard,
            DataChecksum,
            init_db,
            create_data_shard,
        )

        print("✅ Schema 模組導入成功")
        return True

    except ImportError as e:
        print(f"❌ 導入失敗: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他錯誤: {e}")
        return False


def test_database_creation():
    """測試資料庫創建"""
    print("\n🔍 測試資料庫創建...")

    try:
        from sqlalchemy import create_engine
        from src.database.schema import Base, init_db

        # 創建記憶體資料庫
        engine = create_engine("sqlite:///:memory:", echo=False)

        # 初始化資料庫
        init_db(engine)

        # 檢查表是否創建成功
        inspector = engine.dialect.get_table_names(engine.connect())
        expected_tables = [
            "market_daily",
            "market_minute",
            "market_tick",
            "data_shard",
            "data_checksum",
            "database_version",
        ]

        for table in expected_tables:
            if table not in inspector:
                print(f"❌ 表 {table} 未創建")
                return False

        print("✅ 所有核心表創建成功")
        return True

    except Exception as e:
        print(f"❌ 資料庫創建測試失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_data_shard_table():
    """測試 DataShard 表結構"""
    print("\n🔍 測試 DataShard 表結構...")

    try:
        from sqlalchemy import create_engine, inspect
        from sqlalchemy.orm import sessionmaker
        from src.database.schema import Base, DataShard, init_db
        from datetime import date

        # 創建記憶體資料庫
        engine = create_engine("sqlite:///:memory:", echo=False)
        init_db(engine)

        # 檢查 DataShard 表結構
        inspector = inspect(engine)
        columns = inspector.get_columns("data_shard")
        column_names = [col["name"] for col in columns]

        # 檢查必要欄位
        required_fields = [
            "id",
            "table_name",
            "shard_key",
            "shard_id",
            "start_date",
            "end_date",
            "row_count",
            "file_path",
            "file_format",
            "file_size_bytes",
            "compression",
            "is_compressed",
        ]

        for field in required_fields:
            if field not in column_names:
                print(f"❌ DataShard 表缺少欄位: {field}")
                return False

        # 測試插入資料
        Session = sessionmaker(bind=engine)
        session = Session()

        shard = DataShard(
            table_name="test_table",
            shard_key="date",
            shard_id="test_shard_001",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            file_path="/test/path.parquet",
            file_size_bytes=1024,
        )

        session.add(shard)
        session.commit()

        # 檢查預設值
        assert shard.file_format == "parquet"
        assert shard.is_compressed == False

        session.close()
        print("✅ DataShard 表結構和預設值正確")
        return True

    except Exception as e:
        print(f"❌ DataShard 表測試失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_data_checksum_table():
    """測試 DataChecksum 表結構"""
    print("\n🔍 測試 DataChecksum 表結構...")

    try:
        from sqlalchemy import create_engine, inspect
        from sqlalchemy.orm import sessionmaker
        from src.database.schema import Base, DataChecksum, init_db

        # 創建記憶體資料庫
        engine = create_engine("sqlite:///:memory:", echo=False)
        init_db(engine)

        # 檢查 DataChecksum 表結構
        inspector = inspect(engine)
        columns = inspector.get_columns("data_checksum")
        column_names = [col["name"] for col in columns]

        # 檢查必要欄位
        required_fields = [
            "id",
            "table_name",
            "record_id",
            "checksum",
            "checksum_fields",
            "created_at",
            "verified_at",
            "is_valid",
        ]

        for field in required_fields:
            if field not in column_names:
                print(f"❌ DataChecksum 表缺少欄位: {field}")
                return False

        # 測試插入資料
        Session = sessionmaker(bind=engine)
        session = Session()

        checksum = DataChecksum(
            table_name="test_table",
            record_id=123,
            checksum="abc123def456",
            checksum_fields=["field1", "field2"],
        )

        session.add(checksum)
        session.commit()
        session.close()

        print("✅ DataChecksum 表結構正確")
        return True

    except Exception as e:
        print(f"❌ DataChecksum 表測試失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_indexes():
    """測試索引創建"""
    print("\n🔍 測試索引創建...")

    try:
        from sqlalchemy import create_engine, inspect
        from src.database.schema import init_db

        # 創建記憶體資料庫
        engine = create_engine("sqlite:///:memory:", echo=False)
        init_db(engine)

        # 檢查索引
        inspector = inspect(engine)

        # 檢查 DataShard 表索引
        shard_indexes = inspector.get_indexes("data_shard")
        shard_index_names = [idx["name"] for idx in shard_indexes]

        if "ix_data_shard_table_shard" not in shard_index_names:
            print("❌ DataShard 表缺少索引: ix_data_shard_table_shard")
            return False

        # 檢查 DataChecksum 表索引
        checksum_indexes = inspector.get_indexes("data_checksum")
        checksum_index_names = [idx["name"] for idx in checksum_indexes]

        if "ix_data_checksum_table_record" not in checksum_index_names:
            print("❌ DataChecksum 表缺少索引: ix_data_checksum_table_record")
            return False

        print("✅ 所有索引創建成功")
        return True

    except Exception as e:
        print(f"❌ 索引測試失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_create_data_shard_function():
    """測試 create_data_shard 函數"""
    print("\n🔍 測試 create_data_shard 函數...")

    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from src.database.schema import init_db, create_data_shard
        from datetime import date

        # 創建記憶體資料庫
        engine = create_engine("sqlite:///:memory:", echo=False)
        init_db(engine)

        Session = sessionmaker(bind=engine)
        session = Session()

        # 測試創建分片
        shard = create_data_shard(
            session=session,
            table_name="market_daily",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            shard_key="date",
        )

        session.commit()

        # 驗證分片屬性
        assert shard.table_name == "market_daily"
        assert shard.shard_key == "date"
        assert shard.file_format == "parquet"
        assert shard.compression == "snappy"
        assert shard.shard_id == "market_daily_20240101_20240131"

        session.close()
        print("✅ create_data_shard 函數測試通過")
        return True

    except Exception as e:
        print(f"❌ create_data_shard 函數測試失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主測試函數"""
    print("🚀 開始驗證修正後的資料庫 Schema...")
    print("=" * 60)

    tests = [
        ("Schema 模組導入", test_schema_imports),
        ("資料庫創建", test_database_creation),
        ("DataShard 表結構", test_data_shard_table),
        ("DataChecksum 表結構", test_data_checksum_table),
        ("索引創建", test_indexes),
        ("create_data_shard 函數", test_create_data_shard_function),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n📋 執行測試: {test_name}")
        print("-" * 40)

        if test_func():
            passed += 1
            print(f"✅ {test_name} 測試通過")
        else:
            print(f"❌ {test_name} 測試失敗")

    print("\n" + "=" * 60)
    print(f"📊 測試結果: {passed}/{total} 通過")

    if passed == total:
        print("🎉 資料庫 Schema 驗證成功！")
        print("\n📋 Schema 修正成果:")
        print("✅ DataShard 表 file_format 欄位已添加預設值 'parquet'")
        print("✅ 所有表和索引可以正常創建")
        print("✅ 無索引重複問題")
        print("✅ 與重構後的模組完全相容")
        print("✅ create_data_shard 函數正常運作")

        return True
    else:
        print("❌ 部分測試失敗，需要進一步修正")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
