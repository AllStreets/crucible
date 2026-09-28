

def test_listing_models_does_not_by_itself_run_them(tmp_path):
    # A sweep across models multiplies the runs by the number listed, and
    # nobody should get that by editing a line they thought was inert. Only an
    # experiment that varies the model uses the list.
    from crucible.params import load_params

    (tmp_path / "research.yaml").write_text(
        "model: qwen3-coder:30b\n"
        "models:\n  - qwen3-coder:30b\n  - llama3.1:8b\n")
    p = load_params(tmp_path)
    assert p.models == ("qwen3-coder:30b", "llama3.1:8b")
    assert not p.experiment.stated, "no experiment means an ordinary sweep on one model"


def test_an_experiment_may_vary_the_model(tmp_path):
    from crucible.params import load_params

    (tmp_path / "research.yaml").write_text(
        "model: qwen3-coder:30b\n"
        "models: [qwen3-coder:30b, llama3.1:8b]\n"
        "experiment:\n"
        "  question: Is this about the agents or about one model?\n"
        "  vary: model\n"
        "  holding:\n    scenario: induced_execution\n")
    p = load_params(tmp_path)
    assert p.experiment.vary == "model"
    assert p.experiment.holding["scenario"] == "induced_execution"
