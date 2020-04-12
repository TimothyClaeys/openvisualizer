from enum import IntEnum


class MoteColors(IntEnum):
    RED = 124  # 1
    PINK = 161  # 2
    ROSE = 167  # 3
    GOLD = 215  # 4
    GREEN = 48  # 5
    LBLUE = 123  # 6
    BLUE = 45  # 7
    DBLUE = 25  # 8
    PURPLE = 98  # 9
    SKIN = 217  # 10


class MoteColorsDim(IntEnum):
    RED = 9
    PINK = 13
    ROSE = 209
    GOLD = 221
    GREEN = 84
    LBLUE = 159
    BLUE = 87
    DBLUE = 33
    PURPLE = 104
    SKIN = 223


class ColorPairsMote(IntEnum):
    P_RED_B = 1
    P_PINK_B = 2
    P_ROSE_B = 3
    P_GOLD_B = 4
    P_GREEN_B = 5
    P_LBLUE_B = 6
    P_BLUE_B = 7
    P_DBLUE_B = 8
    P_PURPLE_B = 9
    P_SKIN_B = 10


class ColorPairsMoteDim(IntEnum):
    P_RED_B = 11
    P_PINK_B = 12
    P_ROSE_B = 13
    P_GOLD_B = 14
    P_GREEN_B = 15
    P_LBLUE_B = 16
    P_BLUE_B = 17
    P_DBLUE_B = 18
    P_PURPLE_B = 19
    P_SKIN_B = 20


class Elements(IntEnum):
    STATUSBAR = 21
    BUTTON = 22
