from app.execution_profiles import (
    EXECUTION_PROFILES,
    get_execution_profile,
)


def test_eco_profile() -> None:
    profile = get_execution_profile("eco")

    assert profile.name == "eco"
    assert profile.intra_op_num_threads == 1
    assert profile.inter_op_num_threads == 1
    assert profile.execution_mode == "sequential"
    assert profile.allow_spinning is False


def test_balanced_profile_matches_default_ort_strategy() -> None:
    profile = get_execution_profile("balanced")

    assert profile.name == "balanced"
    assert profile.intra_op_num_threads == 0
    assert profile.inter_op_num_threads == 0
    assert profile.execution_mode == "sequential"
    assert profile.allow_spinning is True


def test_profiles_have_expected_names() -> None:
    assert set(EXECUTION_PROFILES) == {
        "eco",
        "balanced",
    }


def test_profile_serialization() -> None:
    profile = get_execution_profile("eco")

    assert profile.as_dict() == {
        "name": "eco",
        "intra_op_num_threads": 1,
        "inter_op_num_threads": 1,
        "execution_mode": "sequential",
        "allow_spinning": False,
    }
