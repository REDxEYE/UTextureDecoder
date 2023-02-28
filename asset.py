from dataclasses import dataclass, field
from uuid import UUID

from engine_version import EngineVersion
from file_utils import Buffer


@dataclass
class Name:
    value: str
    ihash: int
    hash: int

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        return cls(buffer.read_ue_string(), buffer.read_uint16(), buffer.read_uint16())

    def __str__(self):
        return self.value


def read_name(buffer, name_map: list[Name]):
    name_index = buffer.read_int32()
    name_number = buffer.read_int32()
    name = name_map[name_index].value + (f"_{name_number}" if name_number > 0 else "")
    return name


@dataclass
class UEImportObject:
    class_package: str
    class_name: str
    outer_index: int
    object_name: str
    outer_package: object

    @classmethod
    def from_buffer(cls, buffer: Buffer, name_map: list[Name]):
        return cls(read_name(buffer, name_map),
                   read_name(buffer, name_map),
                   buffer.read_int32(),
                   read_name(buffer, name_map),
                   None)


@dataclass
class UEPackageIndex:
    index: int
    obj_import: UEImportObject | None

    @classmethod
    def from_buffer(cls, buffer: Buffer, import_list: list[UEImportObject]):
        index = buffer.read_int32()
        return cls(index, import_list[index * -1 - 1] if index < 0 else None)


@dataclass
class UEObjectExport:
    class_index: UEPackageIndex
    super_index: UEPackageIndex
    template_index: UEPackageIndex
    outer_index: UEPackageIndex
    object_name: str
    save: int
    serial_size: int
    serial_offset: int
    forced_export: bool
    not_for_client: bool
    not_for_server: bool
    package_guid: UUID
    package_flags: int
    not_always_loaded_for_editor_game: bool
    is_asset: bool
    first_export_dependency: int
    serialization_before_serialization_dependencies: bool
    create_before_serialization_dependencies: bool
    serialization_before_create_dependencies: bool
    create_before_create_dependencies: bool

    @classmethod
    def from_buffer(cls, buffer: Buffer, name_map: list[Name], import_list: list[UEImportObject]):
        return cls(
            UEPackageIndex.from_buffer(buffer, import_list),
            UEPackageIndex.from_buffer(buffer, import_list),
            UEPackageIndex.from_buffer(buffer, import_list),
            UEPackageIndex.from_buffer(buffer, import_list),
            read_name(buffer, name_map),
            buffer.read_uint32(),
            buffer.read_int64(),
            buffer.read_int64(),
            buffer.read_int32(),
            buffer.read_int32(),
            buffer.read_int32(),
            UUID(bytes=buffer.read(16)),
            buffer.read_uint32(),
            buffer.read_uint32() != 0,
            buffer.read_uint32() != 0,
            buffer.read_uint32(),
            buffer.read_uint32() != 0,
            buffer.read_uint32() != 0,
            buffer.read_uint32() != 0,
            buffer.read_uint32() != 0,
        )


@dataclass
class UEAsset:
    legacy_version: int
    file_version: int
    file_licensee_version: int
    folder_name: str
    package_flags: int
    imported_objects: list[UEImportObject] = field(repr=False)
    exported_objects: list[UEObjectExport] = field(repr=False)
    export_size: int
    total_header_size: int
    name_map: list[Name] = field(repr=False)

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        assert buffer.read_uint32() == 0x9E2A83C1
        legacy_version = buffer.read_int32()
        assert legacy_version == -7
        legacy_ue3_version = buffer.read_uint32()
        file_version = buffer.read_uint32()
        file_licensee_version = buffer.read_uint32()
        custom_version_count = buffer.read_uint32()
        assert custom_version_count == 0
        buffer.skip(custom_version_count * 20)
        total_header_size = buffer.read_uint32()
        folder_name = buffer.read_ue_string()
        package_flags = buffer.read_uint32()
        name_count, name_offset = buffer.read_fmt("2I")
        gatherable_text_data_count, gatherable_text_data_offset = buffer.read_fmt("2I")
        export_count, export_offset = buffer.read_fmt("2I")
        import_count, import_offset = buffer.read_fmt("2I")
        depends_offset = buffer.read_uint32()
        string_asset_references_count, string_asset_references_offset = buffer.read_fmt("2I")
        searchable_names_offset, thumbnail_table_offset = buffer.read_fmt("2I")
        guid = UUID(bytes=buffer.read(16))
        generations = [buffer.read_fmt("2i") for _ in range(buffer.read_uint32())]
        saved_by = EngineVersion.from_buffer(buffer)
        compatible_with = EngineVersion.from_buffer(buffer)
        compression_flags = buffer.read_uint32()
        compressed_chunks = [buffer.read_fmt("4i") for _ in range(buffer.read_uint32())]
        package_source = buffer.read_uint32()
        additional_packages_to_cook = [buffer.read_ue_string() for _ in range(buffer.read_uint32())]
        build_data_start_offset = buffer.read_uint32()
        wold_tile_info_data_offset = buffer.read_uint32()
        chunk_ids = [buffer.read_int32() for _ in range(buffer.read_uint32())]
        preload_dependency_count = buffer.read_uint32()
        preload_dependency_offset = buffer.read_uint32()
        with buffer.read_from_offset(name_offset):
            name_map: list[Name] = [Name.from_buffer(buffer) for _ in range(name_count)]
        imported_objects = []
        with buffer.read_from_offset(import_offset):
            for _ in range(import_count):
                imported_objects.append(UEImportObject.from_buffer(buffer, name_map))
        for obj in imported_objects:
            if obj.outer_index < 0:
                obj.outer_package = imported_objects[obj.outer_index * -1 - 1]

        exported_objects = []
        with buffer.read_from_offset(export_offset):
            for _ in range(export_count):
                exported_objects.append(UEObjectExport.from_buffer(buffer, name_map, imported_objects))
        export_size = sum(exported_object.serial_size for exported_object in exported_objects)
        return cls(legacy_version, file_version, file_licensee_version, folder_name, package_flags,
                   imported_objects, exported_objects, export_size, total_header_size, name_map)
