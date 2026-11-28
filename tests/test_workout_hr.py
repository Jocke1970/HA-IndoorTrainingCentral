import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("workout_hr", Path(__file__).parents[1] / "custom_components/homefitnesscode/workout.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_external_hr_replay(tmp_path):
    path = tmp_path / "pass.jsonl"
    rows = [{"type": "session_start", "hr_source_id": "m7", "hr_source_name": "M7"},
            {"type": "heart_rate", "source_id": "m7", "bpm": 100},
            {"type": "heart_rate", "source_id": "m7", "bpm": 120},
            {"type": "session_end", "reason": "stopped"}]
    path.write_text("\n".join(json.dumps(row) for row in rows))
    result = module.replay_session(path)
    assert result["average_heart_rate_bpm"] == 110
    assert result["max_heart_rate_bpm"] == 120
    assert result["heart_rate_samples"] == 2
    assert result["heart_rate_source"] == "M7"
