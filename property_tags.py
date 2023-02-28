from dataclasses import dataclass
from typing import Type, Any
from uuid import UUID

from asset import Name, read_name
from file_utils import Buffer


class UEPropertyTagData:
    @classmethod
    def from_buffer(cls, buffer: Buffer, name_map: list[Name]):
        raise NotImplementedError()


@dataclass
class UEStructPropertyTagData(UEPropertyTagData):
    name: str
    guid: UUID

    @classmethod
    def from_buffer(cls, buffer: Buffer, name_map: list[Name]):
        return cls(read_name(buffer, name_map), UUID(bytes=buffer.read(16)))


class UEBoolPropertyTagData(UEPropertyTagData, int):
    @classmethod
    def from_buffer(cls, buffer: Buffer, name_map: list[Name]):
        return cls(buffer.read_uint8())


@dataclass
class UEEnumPropertyTagData(UEPropertyTagData):
    value: str

    @classmethod
    def from_buffer(cls, buffer: Buffer, name_map: list[Name]):
        return cls(read_name(buffer, name_map))


@dataclass
class UEBytePropertyTagData(UEPropertyTagData):
    value: str

    @classmethod
    def from_buffer(cls, buffer: Buffer, name_map: list[Name]):
        return cls(read_name(buffer, name_map))


@dataclass
class UEArrayPropertyTagData(UEPropertyTagData):
    value: str

    @classmethod
    def from_buffer(cls, buffer: Buffer, name_map: list[Name]):
        return cls(read_name(buffer, name_map))


@dataclass
class UEMapPropertyTagData(UEPropertyTagData):
    key_type: str
    value_type: str

    @classmethod
    def from_buffer(cls, buffer: Buffer, name_map: list[Name]):
        return cls(read_name(buffer, name_map), read_name(buffer, name_map))


@dataclass
class UESetPropertyTagData(UEPropertyTagData):
    value_type: str

    @classmethod
    def from_buffer(cls, buffer: Buffer, name_map: list[Name]):
        return cls(read_name(buffer, name_map))


TAG_DATA: dict[str, Type[UEPropertyTagData]] = {
    "StructProperty": UEStructPropertyTagData,
    "BoolProperty": UEBoolPropertyTagData,
    "EnumProperty": UEEnumPropertyTagData,
    "ByteProperty": UEBytePropertyTagData,
    "ArrayProperty": UEArrayPropertyTagData,
    "MapProperty": UEMapPropertyTagData,
    "SetProperty": UESetPropertyTagData,
}


class UEPropertyTag:
    @classmethod
    def from_buffer_and_tag_data(cls, buffer: Buffer, name_map: list[Name], tag_data: UEPropertyTagData):
        raise NotImplementedError()


class UEBoolPropertyTag(UEPropertyTag, int):

    @classmethod
    def from_buffer_and_tag_data(cls, buffer: Buffer, name_map: list[Name], tag_data: UEPropertyTagData):
        assert isinstance(tag_data, UEBoolPropertyTagData)
        return cls(tag_data)


class UEInt8PropertyTag(UEPropertyTag, int):

    @classmethod
    def from_buffer_and_tag_data(cls, buffer: Buffer, name_map: list[Name], tag_data: UEPropertyTagData):
        return cls(buffer.read_int8())


class UEInt16PropertyTag(UEPropertyTag, int):

    @classmethod
    def from_buffer_and_tag_data(cls, buffer: Buffer, name_map: list[Name], tag_data: UEPropertyTagData):
        return cls(buffer.read_int16())


class UEUInt16PropertyTag(UEPropertyTag, int):

    @classmethod
    def from_buffer_and_tag_data(cls, buffer: Buffer, name_map: list[Name], tag_data: UEPropertyTagData):
        return cls(buffer.read_uint16())


class UEIntPropertyTag(UEPropertyTag, int):

    @classmethod
    def from_buffer_and_tag_data(cls, buffer: Buffer, name_map: list[Name], tag_data: UEPropertyTagData):
        return cls(buffer.read_int32())


class UEUInt32PropertyTag(UEPropertyTag, int):

    @classmethod
    def from_buffer_and_tag_data(cls, buffer: Buffer, name_map: list[Name], tag_data: UEPropertyTagData):
        return cls(buffer.read_uint32())


class UEUInt64PropertyTag(UEPropertyTag, int):

    @classmethod
    def from_buffer_and_tag_data(cls, buffer: Buffer, name_map: list[Name], tag_data: UEPropertyTagData):
        return cls(buffer.read_uint64())


class UEFloatPropertyTag(UEPropertyTag, float):

    @classmethod
    def from_buffer_and_tag_data(cls, buffer: Buffer, name_map: list[Name], tag_data: UEPropertyTagData):
        return cls(buffer.read_float())


@dataclass
class UENamePropertyTag(UEPropertyTag):
    value: str

    @classmethod
    def from_buffer_and_tag_data(cls, buffer: Buffer, name_map: list[Name], tag_data: UEPropertyTagData):
        raise NotImplementedError()


class UEBytePropertyTag(UEPropertyTag, int):

    @classmethod
    def from_buffer_and_tag_data(cls, buffer: Buffer, name_map: list[Name], tag_data: UEPropertyTagData):
        assert isinstance(tag_data, UEBytePropertyTagData)
        if tag_data.value == "None":
            return cls(buffer.read_uint8())
        return UENamePropertyTag(read_name(buffer, name_map))


class UEStructPropertyTag(UEPropertyTag, dict[str, Any]):
    @classmethod
    def from_buffer_and_tag_data(cls, buffer: Buffer, name_map: list[Name], tag_data: UEPropertyTagData):
        assert isinstance(tag_data, UEStructPropertyTagData)
        name = tag_data.name
        if name == "IntPoint":
            return cls(x=UEUInt32PropertyTag(buffer.read_uint32()), y=UEUInt32PropertyTag(buffer.read_uint32()))
        elif name == "Guid":
            return cls(
                a=UEUInt32PropertyTag(buffer.read_uint32()),
                b=UEUInt32PropertyTag(buffer.read_uint32()),
                c=UEUInt32PropertyTag(buffer.read_uint32()),
                d=UEUInt32PropertyTag(buffer.read_uint32()),
            )
        raise NotImplementedError()


TAGS: dict[str, Type[UEPropertyTag]] = {
    "StructProperty": UEStructPropertyTag,
    "BoolProperty": UEBoolPropertyTag,
    "FloatProperty": UEFloatPropertyTag,
    "IntProperty": UEIntPropertyTag,
    "Int8Property": UEInt8PropertyTag,
    "Int16Property": UEInt16PropertyTag,
    "UInt16Property": UEUInt16PropertyTag,
    "UInt32Property": UEUInt32PropertyTag,
    "UInt64Property": UEUInt64PropertyTag,
    # "EnumProperty": UEEnumPropertyTag,
    "ByteProperty": UEBytePropertyTag,
    # "ArrayProperty": UEArrayPropertyTag,
    # "MapProperty": UEMapPropertyTag,
    # "SetProperty": UESetPropertyTag,
}


@dataclass
class UEPropertyTag:
    name: str
    type: str
    data: UEPropertyTagData | None
    size: int
    array_index: int
    guid: UUID
    tag: UEPropertyTag
