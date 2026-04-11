from brambhand.scenario.replay_log import ReplayLog


def test_replay_log_jsonl_roundtrip(tmp_path) -> None:
    log = ReplayLog.empty()
    log.append(sim_time_s=0.0, kind="simulation_started", payload={"dt": 10.0})
    log.append(sim_time_s=10.0, kind="burn_started", payload={"vehicle": "sat", "throttle": 0.5})
    log.append(sim_time_s=20.0, kind="burn_ended", payload={"vehicle": "sat"})

    path = tmp_path / "replay.jsonl"
    log.save_jsonl(path)

    loaded = ReplayLog.load_jsonl(path)

    assert loaded.records == log.records
    assert [r.sequence for r in loaded.records] == [0, 1, 2]
