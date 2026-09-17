from app.config import settings
from app.security import session_secret


def test_session_secret_prefers_env():
    settings.session_secret = "from-env"
    assert session_secret() == "from-env"


def test_session_secret_persists_in_data_dir(tmp_path):
    settings.session_secret = ""
    settings.data_dir = tmp_path
    first = session_secret()
    second = session_secret()
    assert first == second
    assert (tmp_path / ".session_secret").read_text(encoding="utf-8").strip() == first
