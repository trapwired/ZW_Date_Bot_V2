"""Unit: people lists come out alphabetically by first name (PrintUtils.sorted_by_display_name)."""
from Enums.Role import Role
from Enums.UserState import UserState
from tests.helpers import seed_user


def test_attendance_name_lists_are_sorted_by_first_name(data_access):
    zoe = seed_user(data_access, 1801, Role.PLAYER, UserState.DEFAULT, first_name='Zoe')
    anna = seed_user(data_access, 1802, Role.PLAYER, UserState.DEFAULT, first_name='Anna')
    mia = seed_user(data_access, 1803, Role.PLAYER, UserState.DEFAULT, first_name='Mia')

    yes, no, unsure = data_access.get_names(([zoe.user_id, anna.user_id, mia.user_id], [], []))

    assert [user.firstname for user in yes] == ['Anna', 'Mia', 'Zoe']
    assert no == [] and unsure == []
