import pytest

from outerram.dense_server import serve


def test_dense_server_refuses_remote_plaintext_before_model_load():
    with pytest.raises(RuntimeError, match="plaintext HTTP"):
        serve("fake", "0.0.0.0", 8080, 4.0)


def test_dense_server_api_key_does_not_make_remote_plaintext_safe():
    with pytest.raises(RuntimeError, match="plaintext HTTP"):
        serve("fake", "0.0.0.0", 8080, 4.0, api_key="secret")
