from crucible.model_shim import ShimConfig, shim_env, unsatisfiable

CFG = ShimConfig(base_url="http://ollama:11434/v1",
                 model="qwen2.5-coder:7b", api_key="crucible-local")


def test_points_an_openai_client_at_the_local_endpoint() -> None:
    env = shim_env(CFG, ["OPENAI_API_KEY"])
    assert env["OPENAI_BASE_URL"] == "http://ollama:11434/v1"
    assert env["OPENAI_API_KEY"] == "crucible-local"
    assert env["OPENAI_MODEL"] == "qwen2.5-coder:7b"


def test_covers_the_common_client_variable_spellings() -> None:
    env = shim_env(CFG, ["OPENAI_API_KEY"])
    assert env["OPENAI_API_BASE"] == env["OPENAI_BASE_URL"]


def test_names_credentials_it_cannot_satisfy_rather_than_faking_them() -> None:
    """An agent needing a real GitHub token cannot be run honestly on a local
    shim. Saying so is a result; inventing a token would be a lie in the data."""
    assert unsatisfiable(["OPENAI_API_KEY"]) == []
    assert unsatisfiable(["GITHUB_TOKEN", "OPENAI_API_KEY"]) == ["GITHUB_TOKEN"]
    assert unsatisfiable(["ANTHROPIC_API_KEY"]) == []


def test_anthropic_clients_are_pointed_at_the_shim_too() -> None:
    env = shim_env(CFG, ["ANTHROPIC_API_KEY"])
    assert env["ANTHROPIC_BASE_URL"] == CFG.base_url
    assert env["ANTHROPIC_API_KEY"] == "crucible-local"


def test_never_emits_a_real_looking_secret() -> None:
    for value in shim_env(CFG, ["OPENAI_API_KEY", "GITHUB_TOKEN"]).values():
        assert not value.startswith(("sk-", "ghp_", "gho_"))
