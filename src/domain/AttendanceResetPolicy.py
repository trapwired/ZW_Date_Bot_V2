"""Domain rule: when does moving an event invalidate everyone's attendance?

If an event is rescheduled by more than this threshold, players' previous YES/NO
answers can no longer be trusted, so they are reset and players are re-asked.
Lives in the domain layer (not the view node) so the rule has one home and a
clear test seam.
"""
import pandas as pd

RESET_THRESHOLD = pd.Timedelta(hours=2)


def requires_attendance_reset(old_timestamp: pd.Timestamp, new_timestamp: pd.Timestamp) -> bool:
    return abs(old_timestamp - new_timestamp) > RESET_THRESHOLD
