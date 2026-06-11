from pathlib import Path

from mio.config import BACKEND_DIR, Settings


def test_settings_env_file_is_independent_of_working_directory(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)

    assert Path(Settings.model_config["env_file"]) == BACKEND_DIR / ".env"
