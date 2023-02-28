from dataclasses import dataclass
from uuid import UUID

from asset import Name, UEImportObject, read_name
from file_utils import Buffer
from property_tags import UEPropertyTag, TAG_DATA, UEPropertyTagData, TAGS


@dataclass
class UEObject(dict[str, UEPropertyTag]):
    export_type: str
    guid: UUID | None

    @classmethod
    def from_buffer(cls, buffer: Buffer, name_map: list[Name], import_list: list[UEImportObject], exported_type: str):
        items = {}
        while True:
            tag = cls.read_prop(buffer, name_map, import_list, True)
            if tag is None:
                break
            items[tag.name] = tag
        guid = UUID(bytes=buffer.read(16)) if buffer.read_uint32() != 0 else None
        self = cls(exported_type, guid)
        self.update(items)
        return self

    @classmethod
    def read_prop(cls, buffer: Buffer, name_map: list[Name], import_list: list[UEImportObject], read_data):
        name = read_name(buffer, name_map)
        if name == "None":
            return None
        prop_type = read_name(buffer, name_map)
        size = buffer.read_int32()
        array_index = buffer.read_int32()

        tag_data_type = TAG_DATA.get(prop_type, None)
        tag_data: UEPropertyTagData | None = None
        if tag_data_type is not None:
            tag_data = tag_data_type.from_buffer(buffer, name_map)
        has_prop_guid = buffer.read_uint8() != 0
        guid: UUID | None = UUID(bytes=buffer.read(16)) if has_prop_guid else None
        start = buffer.tell()
        tag_type = TAGS.get(prop_type, None)
        tag: UEPropertyTag | None = None
        if read_data:
            if tag_type is None:
                raise NotImplementedError(prop_type)
            tag = tag_type.from_buffer_and_tag_data(buffer, name_map, tag_data)

        buffer.seek(start + size)
        return UEPropertyTag(name, prop_type, tag_data, size, array_index, guid, tag)
