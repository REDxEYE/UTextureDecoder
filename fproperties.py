from dataclasses import dataclass, field
from uuid import UUID

from file_utils import Buffer, MemoryBuffer

STRUCT_REGISTRY: dict[UUID, 'FStructProperty'] = {}


@dataclass
class FProperty:
    name: str | None
    type_name: str | None = field(repr=False)
    guid: UUID | None = field(repr=False)
    size: int = field(repr=False)
    data_offset: int = field(init=False)

    @classmethod
    def read_property(cls, buffer: Buffer):
        name = buffer.read_ue_string()
        if name == "None":
            return None

        type_name = buffer.read_ue_string()
        size = buffer.read_int64()

        if type_name == "NameProperty":
            has_guid = buffer.read_uint8()
            assert has_guid in (0, 1)
            guid = None
            if has_guid:
                guid = UUID(bytes=buffer.read(16))
            return FNameProperty(name, type_name, guid, size).from_value(MemoryBuffer(buffer.read(size)), False)
        elif type_name == "StructProperty":
            return FStructProperty(name, type_name, None, size).from_value(buffer, False)
        elif type_name == "ArrayProperty":
            return FArrayProperty(name, type_name, None, size).from_value(buffer, False)
        elif type_name == "ByteProperty":
            return FByteProperty(name, type_name, None, size).from_value(buffer, False)
        elif type_name == "MapProperty":
            return FMapProperty(name, type_name, None, size).from_value(buffer, False)
        elif type_name == "SetProperty":
            return FSetProperty(name, type_name, None, size).from_value(buffer, False)
        elif type_name == "StrProperty":
            has_guid = buffer.read_uint8()
            assert has_guid in (0, 1)
            guid = None
            if has_guid:
                guid = UUID(bytes=buffer.read(16))
            return FStrProperty(name, type_name, guid, size).from_value(buffer, False)
        elif type_name == "IntProperty":
            has_guid = buffer.read_uint8()
            assert has_guid in (0, 1)
            guid = None
            if has_guid:
                guid = UUID(bytes=buffer.read(16))
            return FIntProperty(name, type_name, guid, size).from_value(buffer, False)
        elif type_name == "Int64Property":
            return FInt64Property(name, type_name, None, size).from_value(buffer, False)
        elif type_name == "BoolProperty":
            return FBoolProperty(name, type_name, None, size).from_value(buffer, False)
        elif type_name == "FloatProperty":
            has_guid = buffer.read_uint8()
            assert has_guid in (0, 1)
            guid = None
            if has_guid:
                guid = UUID(bytes=buffer.read(16))
            return FFloatProperty(name, type_name, guid, size).from_value(buffer, False)
        elif type_name == "TextProperty":
            has_guid = buffer.read_uint8()
            assert has_guid in (0, 1)
            guid = None
            if has_guid:
                guid = UUID(bytes=buffer.read(16))
            return FTextProperty(name, type_name, guid, size).from_value(buffer, False)
        elif type_name == "SoftObjectProperty":
            has_guid = buffer.read_uint8()
            assert has_guid in (0, 1)
            guid = None
            if has_guid:
                guid = UUID(bytes=buffer.read(16))
            return FSoftObjectProperty(name, type_name, guid, size).from_value(buffer, False)
        elif type_name == "ObjectProperty":
            has_guid = buffer.read_uint8()
            assert has_guid in (0, 1)
            guid = None
            if has_guid:
                guid = UUID(bytes=buffer.read(16))
            return FObjectProperty(name, type_name, guid, size).from_value(buffer, False)
        else:
            raise NotImplementedError(f"{type_name} not implemented")

    def read_property_array(self, buffer: Buffer, count: int):
        name = buffer.read_ue_string()
        if name == "None":
            return None

        type_name = buffer.read_ue_string()
        size = buffer.read_int64()
        items = []
        for i in range(count):
            if type_name == "NameProperty":
                items.append(
                    FNameProperty(name, type_name, None, size).from_value(MemoryBuffer(buffer.read(size)), False))
            elif type_name == "StructProperty":
                items.append(FStructProperty(name, type_name, None, size).from_value(buffer, i != 0))
            elif type_name == "ArrayProperty":
                items.append(FArrayProperty(name, type_name, None, size).from_value(buffer, i != 0))
            elif type_name == "TextProperty":
                items.append(FTextProperty(name, type_name, None, size).from_value(buffer, i != 0))
            elif type_name == "SoftObjectProperty":
                items.append(FSoftObjectProperty(name, type_name, None, size).from_value(buffer, i != 0))
            elif type_name == "ObjectProperty":
                items.append(FObjectProperty(name, type_name, None, size).from_value(buffer, i != 0))
            elif type_name == "IntProperty":
                items.append(FIntProperty(name, type_name, None, size).from_value(buffer, i != 0))
            elif type_name == "StrProperty":
                items.append(FStrProperty(name, type_name, None, size).from_value(buffer, i != 0))
            elif type_name == "BoolProperty":
                items.append(FBoolProperty(name, type_name, None, size).from_value(buffer, i != 0))
            else:
                raise NotImplementedError(f"{type_name} not implemented")
        return items

    def from_value(self, buffer: Buffer, only_body: bool):
        raise NotImplementedError()


@dataclass
class DummyFProperty(FProperty):
    data: Buffer

    def from_value(self, buffer: Buffer, only_body: bool):
        self.data = buffer
        return self


class FMapProperty(FProperty, dict[str, FProperty]):
    unknown: int = field(init=False)

    def from_value(self, buffer: Buffer, only_body: bool):
        key_type = buffer.read_ue_string()
        assert key_type == "StrProperty"
        value_type = buffer.read_ue_string()
        assert value_type == "StructProperty"
        if buffer.read_uint8():
            self.guid = UUID(bytes=buffer.read(16))
        self.unknown = buffer.read_int32()
        count = buffer.read_int32()
        self.data_offset = buffer.tell()
        for _ in range(count):
            key = buffer.read_ue_string()
            value = FStructProperty(key, value_type, None, -1).from_value(buffer, True)
            self[key] = value
        #     key = self.read_property(buffer)
        #     value = self.read_property(buffer)
        return self


class FSetProperty(FProperty, list[FProperty]):
    unknown: int = field(init=False)

    def from_value(self, buffer: Buffer, only_body: bool):
        item_type = buffer.read_ue_string()
        if buffer.read_uint8():
            self.guid = UUID(bytes=buffer.read(16))
        self.unknown = buffer.read_uint32()
        count = buffer.read_uint32()
        self.data_offset = buffer.tell()
        for _ in range(count):
            if item_type == "ObjectProperty":
                self.append(buffer.read_ue_string())
            else:
                raise NotImplementedError()
        return self


class FStructProperty(FProperty, dict[str, FProperty]):
    def from_value(self, buffer: Buffer, only_body: bool):
        if not only_body:
            inner_type_name = buffer.read_ue_string()
            self.type_name = inner_type_name
            struct_guid = UUID(bytes=buffer.read(16))
            buffer.skip(1)
            if self.size == 0:
                self.data_offset = buffer.tell()
                return self
        else:
            inner_type_name = self.type_name
        self.data_offset = buffer.tell()
        if inner_type_name == "Vector":
            prop = self["X"] = FFloatProperty("X", "FloatProperty", None, 4)
            prop.value = buffer.read_float()
            prop = self["Y"] = FFloatProperty("Y", "FloatProperty", None, 4)
            prop.value = buffer.read_float()
            prop = self["Z"] = FFloatProperty("Z", "FloatProperty", None, 4)
            prop.value = buffer.read_float()
            return self
        elif inner_type_name == "Quat":
            prop = self["X"] = FFloatProperty("X", "FloatProperty", None, 4)
            prop.value = buffer.read_float()
            prop = self["Y"] = FFloatProperty("Y", "FloatProperty", None, 4)
            prop.value = buffer.read_float()
            prop = self["Z"] = FFloatProperty("Z", "FloatProperty", None, 4)
            prop.value = buffer.read_float()
            prop = self["W"] = FFloatProperty("W", "FloatProperty", None, 4)
            prop.value = buffer.read_float()
            return self
        elif inner_type_name == "LinearColor":
            prop = self["R"] = FFloatProperty("X", "FloatProperty", None, 4)
            prop.value = buffer.read_float()
            prop = self["G"] = FFloatProperty("Y", "FloatProperty", None, 4)
            prop.value = buffer.read_float()
            prop = self["B"] = FFloatProperty("Z", "FloatProperty", None, 4)
            prop.value = buffer.read_float()
            prop = self["A"] = FFloatProperty("W", "FloatProperty", None, 4)
            prop.value = buffer.read_float()
            return self
        elif inner_type_name == "Timespan":
            prop = self["Ticks"] = FInt64Property("Ticks", "Int64Property", None, 4)
            prop.value = buffer.read_int64()
            return self
        elif inner_type_name == "DateTime":
            prop = self["Ticks"] = FInt64Property("Ticks", "Int64Property", None, 4)
            prop.value = buffer.read_int64()
            return self
        elif inner_type_name == "GameplayTagContainer":
            prop = self["Tags"] = FTagContainerProperty("Tag", "TagContainerProperty", None, 4)
            count = buffer.read_int32()
            for _ in range(count):
                prop.append(buffer.read_ue_string())
            return self
        elif inner_type_name == "Guid":
            prop = self["GUID"] = FGuidProperty("GUID", "GuidProperty", None, 16)
            prop.value = UUID(bytes=buffer.read(16))
            return self

        while True:
            prop = self.read_property(buffer)
            if prop is None:
                break
            self[prop.name] = prop
        return self


class FArrayProperty(FProperty, list[FProperty]):

    def from_value(self, buffer: Buffer, only_body: bool):
        elem_type = buffer.read_ue_string()
        assert buffer.read_uint8() == 0
        elem_count = buffer.read_uint32()
        if elem_count == 0:
            return self
        self.data_offset = buffer.tell()
        self.extend(self.read_property_array(buffer, elem_count))
        return self


class FByteProperty(FProperty):
    enum_name: str = field(init=False)
    payload: bytes = field(init=False)
    value: str = field(init=False)

    def from_value(self, buffer: Buffer, only_body: bool):
        self.data_offset = buffer.tell()
        if not only_body:
            self.enum_name = buffer.read_ue_string()
            assert buffer.read_uint8() == 0
            self.payload = buffer.read(self.size)
        else:
            self.payload = buffer.read(1)
        if len(self.payload) > 4 and MemoryBuffer(self.payload).read_int32() == self.size - 4:
            self.value = MemoryBuffer(self.payload).read_ue_string()
        return self


class FTagContainerProperty(FProperty, list[str]):

    def from_value(self, buffer: Buffer, only_body: bool):
        raise NotImplementedError


class FGuidProperty(FProperty):
    guid: UUID = field(init=False)

    def from_value(self, buffer: Buffer, only_body: bool):
        raise NotImplementedError


@dataclass
class FStrProperty(FProperty):
    value: str = field(init=False)

    def from_value(self, buffer: Buffer, only_body: bool):
        self.data_offset = buffer.tell()
        self.value = buffer.read_ue_string()
        return self


@dataclass
class FSoftObjectProperty(FProperty):
    value: str = field(init=False)
    unknown: int = field(init=False)

    def from_value(self, buffer: Buffer, only_body: bool):
        self.data_offset = buffer.tell()
        self.value = buffer.read_ue_string()
        self.unknown = buffer.read_int32()
        return self


@dataclass
class FObjectProperty(FProperty):
    value: str = field(init=False)

    def from_value(self, buffer: Buffer, only_body: bool):
        self.data_offset = buffer.tell()
        self.value = buffer.read_ue_string()
        return self


@dataclass
class FFloatProperty(FProperty):
    value: float = field(init=False)

    def from_value(self, buffer: Buffer, only_body: bool):
        self.data_offset = buffer.tell()
        self.value = buffer.read_float()
        return self


@dataclass
class FInt64Property(FProperty):
    value: int = field(init=False)

    def from_value(self, buffer: Buffer, only_body: bool):
        self.data_offset = buffer.tell()
        self.value = buffer.read_int64()
        return self


@dataclass
class FBoolProperty(FProperty):
    value: bool = field(init=False)

    def from_value(self, buffer: Buffer, only_body: bool):
        self.data_offset = buffer.tell()
        if only_body:
            self.value = buffer.read_int8() > 0
        else:
            self.value = buffer.read_int16() > 0
        return self


@dataclass
class FIntProperty(FProperty):
    value: int = field(init=False)

    def from_value(self, buffer: Buffer, only_body: bool):
        self.data_offset = buffer.tell()
        self.value = buffer.read_int32()
        return self


@dataclass
class FNameProperty(FProperty):
    value: str = field(init=False)

    def from_value(self, buffer: Buffer, only_body: bool):
        self.data_offset = buffer.tell()
        self.value = buffer.read_ue_string()
        return self


@dataclass
class FTextProperty(FProperty):
    id: str | None = field(init=False, default="")
    value: str | None = field(init=False, default="")
    flags: int = field(init=False)
    other_flag: int | None = field(init=False, default=None)
    unknown: int | None = field(init=False, default=None)

    def from_value(self, buffer: Buffer, only_body: bool):
        self.flags = magic = buffer.read_uint8()
        if magic == 2:
            self.unknown = buffer.read_uint64()
        elif magic in (0, 8):
            self.unknown = buffer.read_uint64()
            if self.unknown & 0xFF000000:
                self.data_offset = buffer.tell()
                return self
            self.other_flag = buffer.read_uint8()
            self.id = buffer.read_ue_string()

        self.data_offset = buffer.tell()
        self.value = buffer.read_ue_string()
        return self
