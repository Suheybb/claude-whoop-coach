"""WHOOP MCP server — gives Claude your recovery, sleep, strain and workouts so it can coach you."""
from statistics import mean

from mcp.server.mcpserver import MCPServer

from . import client

mcp = MCPServer(
    "whoop",
    instructions="WHOOP data for coaching. Start with get_today; use get_trends for progress and overtraining checks.",
)

H = 3_600_000  # ms per hour


def _h(ms) -> float | None:
    return round(ms / H, 2) if ms is not None else None


def _r(x, n=1):
    return round(x, n) if isinstance(x, (int, float)) else None


def _avg(vals):
    vals = [v for v in vals if v is not None]
    return round(mean(vals), 1) if vals else None


# ---------- formatters (raw WHOOP JSON is noisy; keep what a coach needs) ----------

def fmt_recovery(r: dict) -> dict:
    s = r.get("score") or {}
    return {
        "date": r.get("created_at", "")[:10],
        "state": r.get("score_state"),
        "recovery_pct": s.get("recovery_score"),
        "hrv_ms": _r(s.get("hrv_rmssd_milli")),
        "resting_hr": s.get("resting_heart_rate"),
        "spo2_pct": _r(s.get("spo2_percentage")),
        "skin_temp_c": _r(s.get("skin_temp_celsius"), 2),
    }


def fmt_sleep(r: dict) -> dict:
    s = r.get("score") or {}
    st = s.get("stage_summary") or {}
    need = s.get("sleep_needed") or {}
    in_bed = st.get("total_in_bed_time_milli") or 0
    awake = st.get("total_awake_time_milli") or 0
    return {
        "start": r.get("start"),
        "end": r.get("end"),
        "nap": r.get("nap"),
        "state": r.get("score_state"),
        "asleep_h": _h(in_bed - awake) if in_bed else None,
        "in_bed_h": _h(in_bed) if in_bed else None,
        "deep_h": _h(st.get("total_slow_wave_sleep_time_milli")),
        "rem_h": _h(st.get("total_rem_sleep_time_milli")),
        "light_h": _h(st.get("total_light_sleep_time_milli")),
        "disturbances": st.get("disturbance_count"),
        "need_baseline_h": _h(need.get("baseline_milli")),
        "debt_h": _h(need.get("need_from_sleep_debt_milli")),
        "performance_pct": s.get("sleep_performance_percentage"),
        "efficiency_pct": _r(s.get("sleep_efficiency_percentage")),
        "consistency_pct": s.get("sleep_consistency_percentage"),
        "resp_rate": _r(s.get("respiratory_rate")),
    }


def fmt_workout(r: dict) -> dict:
    s = r.get("score") or {}
    z = s.get("zone_durations") or {}
    return {
        "start": r.get("start"),
        "end": r.get("end"),
        "sport": r.get("sport_name"),
        "strain": _r(s.get("strain")),
        "avg_hr": s.get("average_heart_rate"),
        "max_hr": s.get("max_heart_rate"),
        "kcal": round(s["kilojoule"] / 4.184) if s.get("kilojoule") else None,
        "zone_minutes": {k.replace("_milli", ""): round(v / 60000) for k, v in z.items() if v},
    }


def fmt_cycle(r: dict) -> dict:
    s = r.get("score") or {}
    return {
        "start": r.get("start"),
        "end": r.get("end"),
        "state": r.get("score_state"),
        "day_strain": _r(s.get("strain")),
        "kcal": round(s["kilojoule"] / 4.184) if s.get("kilojoule") else None,
        "avg_hr": s.get("average_heart_rate"),
        "max_hr": s.get("max_heart_rate"),
    }


def _main_sleeps(days: int) -> list[dict]:
    return [fmt_sleep(s) for s in client.sleep(days) if not s.get("nap")]


# ---------- tools ----------

@mcp.tool()
def get_today() -> dict:
    """Morning briefing: latest recovery, last night's sleep, current day strain and recent workouts.
    Start here when the user asks how they're doing or what to train today."""
    rec = client.recovery(2)
    slp = _main_sleeps(2)
    cyc = client.cycles(2)
    wk = client.workouts(2)
    return {
        "recovery": fmt_recovery(rec[0]) if rec else None,
        "last_sleep": slp[0] if slp else None,
        "today": fmt_cycle(cyc[0]) if cyc else None,
        "recent_workouts": [fmt_workout(w) for w in wk[:3]],
    }


@mcp.tool()
def get_recovery(days: int = 7) -> list[dict]:
    """Daily recovery %, HRV, resting HR, SpO2 and skin temp for the last N days (newest first)."""
    return [fmt_recovery(r) for r in client.recovery(days)]


@mcp.tool()
def get_sleep(days: int = 7, include_naps: bool = False) -> list[dict]:
    """Sleep records for the last N days: duration, stages, need/debt, performance, consistency."""
    return [fmt_sleep(s) for s in client.sleep(days) if include_naps or not s.get("nap")]


@mcp.tool()
def get_workouts(days: int = 14) -> list[dict]:
    """Workouts for the last N days: sport, strain, heart rate, calories and HR-zone minutes."""
    return [fmt_workout(w) for w in client.workouts(days)]


@mcp.tool()
def get_strain(days: int = 7) -> list[dict]:
    """Daily strain (physiological cycles) for the last N days."""
    return [fmt_cycle(c) for c in client.cycles(days)]


@mcp.tool()
def get_trends(days: int = 30) -> dict:
    """Averages and week-over-week comparison of recovery, HRV, RHR, sleep and strain.
    Use for 'am I improving?', overtraining checks and spotting bad habits."""
    rec = [fmt_recovery(r) for r in client.recovery(days)]
    slp = _main_sleeps(days)
    cyc = [fmt_cycle(c) for c in client.cycles(days)]

    def block(rs, ss, cs):
        return {
            "recovery_pct": _avg(r["recovery_pct"] for r in rs),
            "hrv_ms": _avg(r["hrv_ms"] for r in rs),
            "resting_hr": _avg(r["resting_hr"] for r in rs),
            "sleep_h": _avg(s["asleep_h"] for s in ss),
            "sleep_performance_pct": _avg(s["performance_pct"] for s in ss),
            "sleep_consistency_pct": _avg(s["consistency_pct"] for s in ss),
            "day_strain": _avg(c["day_strain"] for c in cs),
        }

    return {
        "period_days": days,
        "overall": block(rec, slp, cyc),
        "last_7_days": block(rec[:7], slp[:7], cyc[:7]),
        "previous_7_days": block(rec[7:14], slp[7:14], cyc[7:14]),
        "red_days": sum(1 for r in rec if (r["recovery_pct"] or 100) < 34),
        "green_days": sum(1 for r in rec if (r["recovery_pct"] or 0) >= 67),
    }


@mcp.tool()
def get_profile() -> dict:
    """User name plus body measurements (height, weight, max HR)."""
    p, b = client.profile(), client.body()
    return {
        "name": f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(),
        "height_m": b.get("height_meter"),
        "weight_kg": b.get("weight_kilogram"),
        "max_hr": b.get("max_heart_rate"),
    }


# ---------- coaching prompt ----------

@mcp.prompt()
def coach() -> str:
    """Daily coaching check-in."""
    return (
        "You are my performance coach. Call get_today and get_trends(30). Then give me:\n"
        "1. A one-line verdict on my readiness today.\n"
        "2. What to train today and how hard (target strain), based on recovery colour "
        "(green ≥67%, yellow 34–66%, red <34%) and my recent load.\n"
        "3. One sleep fix for tonight (bedtime, consistency, debt).\n"
        "4. Any warning trend (HRV dropping, RHR rising, too many red days).\n"
        "Be direct and brief. Use my numbers, not generic advice."
    )


def main():
    mcp.run()


if __name__ == "__main__":
    main()
