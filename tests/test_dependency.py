"""The architecture depends on reusing SMADP's sandbox rather than forking it.
If this ever fails, the dependency assumption in the spec is broken and the
plan needs revisiting rather than patching."""


def test_smadp_sandbox_is_importable_as_a_library() -> None:
    from smadp.sandbox import runner, properties, tripwire

    assert callable(properties.evaluate_properties)
    assert callable(properties.apply_property_floors)
    assert hasattr(runner, "AdapterDescriptor")
    assert callable(tripwire.check_event)


def test_smadp_ships_the_scenarios_we_intend_to_use() -> None:
    from pathlib import Path
    import smadp.sandbox.scenarios as scenarios

    names = {p.stem for p in Path(scenarios.__file__).parent.glob("*.yaml")}
    # These four are the ones Phase 1's arena bridge targets.
    assert {"state_poisoning", "secret_exfiltration",
            "induced_execution", "partner_escalation"} <= names
