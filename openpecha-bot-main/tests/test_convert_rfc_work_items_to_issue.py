from pathlib import Path

import pytest

from bot.convert_rfc_work_phase_to_milestones import get_milestones_from_work_phase


@pytest.fixture(scope="module")
def rfc():
    rfc_path = Path(__file__).parent / "data" / "rfc.txt"
    return rfc_path.read_text()


def test_get_miliestone_from_work_phase(rfc):
    milestones = get_milestones_from_work_phase(rfc)

    print()
    print(milestones)
