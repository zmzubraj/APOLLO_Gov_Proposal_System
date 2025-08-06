import pathlib, sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from analysis.prediction_analysis import forecast_outcome
from utils.validators import validate_predictions


def test_forecast_outcome_structure_and_range():
    result = forecast_outcome({})
    # Ensure keys exist and values are within [0,1]
    assert validate_predictions(result)
    assert 0 <= result["approval_probability"] <= 1
    assert 0 <= result["turnout"] <= 1
