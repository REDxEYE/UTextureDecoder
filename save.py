from dataclasses import dataclass, field

from custom_version import CustomVersion
from custom_version_serialization_format import CustomVersionSerializationFormat
from engine_version import EngineVersion
from file_utils import Buffer
from fproperties import FProperty, FStructProperty


@dataclass
class UESave:
    unknown0: int | None
    savegame_file_version: int
    package_file_version: int
    engine_version: EngineVersion
    custom_version_format: CustomVersionSerializationFormat
    custom_version: list[CustomVersion] = field(repr=False)
    save_game_class_name: str
    unknown1: int | None

    root: FStructProperty

    @classmethod
    def from_buffer(cls, buffer: Buffer, expect_ident: bool = False):
        if expect_ident:
            assert buffer.read_ascii_string(4) == "GVAS"
            unknown0 = None
        else:
            unknown0 = buffer.read_uint32()
        savegame_file_version = buffer.read_uint32()
        package_file_version = buffer.read_uint32()
        engine_version = EngineVersion.from_buffer(buffer)
        asset = cls(
            unknown0,
            savegame_file_version,
            package_file_version,
            engine_version,
            CustomVersionSerializationFormat(buffer.read_int32()),
            [CustomVersion.from_buffer(buffer) for _ in range(buffer.read_uint32())],
            buffer.read_ue_string(),
            buffer.read_int32() if engine_version.minor > 26 else None,
            FStructProperty(None, None, None, -1)
        )
        asset.root.data_offset = buffer.tell()
        while True:
            prop = FProperty.read_property(buffer)
            print(prop)
            if prop is None:
                break
            asset.root[prop.name] = prop
        return asset
