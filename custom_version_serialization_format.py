from enum import IntEnum


class CustomVersionSerializationFormat(IntEnum):
    Unknown = 0
    Guids = 1
    Enums = 2
    Optimised = 3
    CustomVersion_Automatic_Plus_One = 4
