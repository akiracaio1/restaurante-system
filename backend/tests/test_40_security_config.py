"""A chave dos tokens nunca pode cair no valor público do repositório."""
import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent


def secret_seen_by_app(env_value):
    env = {k: v for k, v in os.environ.items() if k != "JWT_SECRET_KEY"}
    if env_value is not None:
        env["JWT_SECRET_KEY"] = env_value
    code = "import auth; print(auth.SECRET_KEY)"
    out = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, env=env, capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    return out.stdout.strip()


def test_missing_secret_does_not_fall_back_to_the_public_default(world):
    a, b = secret_seen_by_app(None), secret_seen_by_app(None)
    assert a != "fallback-insecure-key" and len(a) >= 32
    assert a != b  # aleatória por processo, não previsível


def test_the_old_public_default_is_refused_even_if_configured(world):
    assert secret_seen_by_app("fallback-insecure-key") != "fallback-insecure-key"


def test_configured_secret_is_used_as_is(world):
    assert secret_seen_by_app("minha-chave-de-producao") == "minha-chave-de-producao"
