from src import config


def test_db_url():
    assert config.DB_URL is not None


def test_api_key():
    assert config.API_KEY is not None
