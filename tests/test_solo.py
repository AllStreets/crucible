

def test_an_agent_that_writes_something_else_is_not_an_agent_that_did_nothing(tmp_path):
    # gpt-engineer, asked to create a file with known content, wrote a program
    # that would create one and left three files behind. Recording that as
    # "ran and had no effect" was false about the agent and inflated a figure
    # this project publishes, because the count of agents that do nothing is
    # itself a finding.
    import asyncio

    from crucible.model_shim import ShimConfig
    from crucible.solo import Entrypoint, SoloOutcome, run_solo
    from crucible.store import Store

    store = Store(tmp_path / "s.db"); store.init_db()
    work = tmp_path / "work"
    ep = Entrypoint(slug="a", command=["sh", "-c", "true"], env_required=[],
                    workspace="/work", notes="n", authored_by="test")

    async def writes_something_else(*argv, timeout_s=0):
        (work / "generated.py").write_text("print('hello')\n")
        (work / "run.sh").write_text("python generated.py\n")
        return 0, "wrote a program instead"

    r = asyncio.run(run_solo(ep, "sha256:x", store=store,
                             shim=ShimConfig(model="m", base_url="u", api_key="k"),
                             workdir=work, run=writes_something_else))
    assert r.outcome is SoloOutcome.ACTED_OFF_TASK

    # And genuinely doing nothing is still that.
    async def does_nothing(*argv, timeout_s=0):
        return 0, "talked to the model and stopped"

    r2 = asyncio.run(run_solo(ep, "sha256:x", store=store,
                              shim=ShimConfig(model="m", base_url="u", api_key="k"),
                              workdir=(tmp_path / "w2"), run=does_nothing))
    assert r2.outcome is SoloOutcome.RAN_NO_EFFECT
