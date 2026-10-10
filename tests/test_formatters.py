from whoop_mcp.server import fmt_recovery, fmt_sleep, fmt_workout


def test_recovery():
    r = fmt_recovery({"created_at": "2026-10-10T06:00:00Z", "score_state": "SCORED",
                      "score": {"recovery_score": 72, "hrv_rmssd_milli": 61.234, "resting_heart_rate": 52}})
    assert r["recovery_pct"] == 72 and r["hrv_ms"] == 61.2 and r["date"] == "2026-10-10"


def test_sleep_pending_does_not_crash():
    s = fmt_sleep({"score_state": "PENDING_SCORE", "nap": False})
    assert s["asleep_h"] is None


def test_sleep_hours():
    s = fmt_sleep({"score": {"stage_summary": {"total_in_bed_time_milli": 8 * 3_600_000,
                                               "total_awake_time_milli": 3_600_000}}})
    assert s["asleep_h"] == 7.0


def test_workout_kcal():
    w = fmt_workout({"sport_name": "running", "score": {"strain": 12.34, "kilojoule": 4184}})
    assert w["kcal"] == 1000 and w["strain"] == 12.3
