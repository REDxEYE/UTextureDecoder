import zlib
from dataclasses import dataclass
from enum import IntEnum, IntFlag

from PIL import Image
from pyzorder import ZOrderIndexer

from asset import UEImportObject, Name, read_name
from file_utils import Buffer, MemoryBuffer
from ue_object import UEObject


class UEBulkDataFlags(IntFlag):
    # Empty flag set. */
    BULKDATA_None = 0
    # If set, payload is stored at the end of the file and not inline. */
    BULKDATA_PayloadAtEndOfFile = 1 << 0
    # If set, payload should be [un]compressed using ZLIB during serialization. */
    BULKDATA_SerializeCompressedZLIB = 1 << 1
    # Force usage of SerializeElement over bulk serialization. */
    BULKDATA_ForceSingleElementSerialization = 1 << 2
    # Bulk data is only used once at runtime in the game. */
    BULKDATA_SingleUse = 1 << 3
    # Bulk data won't be used and doesn't need to be loaded. */
    BULKDATA_Unused = 1 << 5
    # Forces the payload to be saved inline, regardless of its size. */
    BULKDATA_ForceInlinePayload = 1 << 6
    # Flag to check if either compression mode is specified. */
    BULKDATA_SerializeCompressed = BULKDATA_SerializeCompressedZLIB,
    # Forces the payload to be always streamed, regardless of its size. */
    BULKDATA_ForceStreamPayload = 1 << 7
    # If set, payload is stored in a .upack file alongside the uasset. */
    BULKDATA_PayloadInSeperateFile = 1 << 8
    # DEPRECATED: If set, payload is compressed using platform specific bit window. */
    BULKDATA_SerializeCompressedBitWindow = 1 << 9
    # There is a new default to inline unless you opt out. */
    BULKDATA_Force_NOT_InlinePayload = 1 << 10
    # This payload is optional and may not be on device. */
    BULKDATA_OptionalPayload = 1 << 11
    # This payload will be memory mapped, this requires alignment, no compression etc. */
    BULKDATA_MemoryMappedPayload = 1 << 12
    # Bulk data size is 64 bits long. */
    BULKDATA_Size64Bit = 1 << 13
    # Duplicate non-optional payload in optional bulk data. */
    BULKDATA_DuplicateNonOptionalPayload = 1 << 14
    # Indicates that an old ID is present in the data, at some point when the DDCs are flushed we can remove this. */
    BULKDATA_BadDataVersion = 1 << 15
    # BulkData did not have it's offset changed during the cook and does not need the fix up at load time */
    BULKDATA_NoOffsetFixUp = 1 << 16

    # Runtime only flags below this point! Note that they take the high bits in reverse order! */
    # Assigned at runtime to indicate that the BulkData should be using the IoDispatcher when loading, not filepaths. */
    BULKDATA_UsesIoDispatcher = 1 << 31
    # Assigned at runtime to indicate that the BulkData allocation is a memory mapped region of a file and not raw data. */
    BULKDATA_DataIsMemoryMapped = 1 << 30
    # Assigned at runtime to indicate that the BulkData object has an async loading request in flight and will need to wait on it. */
    BULKDATA_HasAsyncReadPending = 1 << 29
    # Assigned at runtime to indicate that the BulkData object should be considered for discard even if it cannot load from disk. */
    BULKDATA_AlwaysAllowDiscard = 1 << 28


@dataclass
class UEByteBulkData:
    bulk_data_flags: UEBulkDataFlags
    element_count: int
    size_on_disk: int
    offset_in_file: int
    inline_data: Buffer | None

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        flags = UEBulkDataFlags(buffer.read_uint32())
        element_count: int
        size_on_disk: int
        offset_in_file: int
        if flags & UEBulkDataFlags.BULKDATA_Size64Bit:
            element_count, size_on_disk = buffer.read_fmt("2Q")
        else:
            element_count, size_on_disk = buffer.read_fmt("2I")
        offset_in_file = buffer.read_uint64()
        inline_data: Buffer | None = None
        if flags & UEBulkDataFlags.BULKDATA_ForceInlinePayload:
            inline_data = MemoryBuffer(buffer.read(size_on_disk))

        return cls(flags, element_count, size_on_disk, offset_in_file, inline_data)


class UEVirtualTextureCodec(IntEnum):
    Black = 0  # Special case codec, always outputs black pixels 0,0,0,0
    OpaqueBlack = 1  # Special case codec, always outputs opaque black pixels 0,0,0,255
    White = 2  # Special case codec, always outputs white pixels 255,255,255,255
    Flat = 3  # Special case codec, always outputs 128,125,255,255 (flat normal map)
    RawGPU = 4  # Uncompressed data in an GPU-ready format (e.g R8G8B8A8, BC7, ASTC, ...)
    ZippedGPU = 5  # Same as RawGPU but with the data zipped
    Crunch = 6  # Use the Crunch library to compress data
    Max = 7  # Add new codecs before this entry


@dataclass
class VirtualTextureDataChunk:
    bulk_data: UEByteBulkData
    size_in_bytes: int
    codec_payload_size: int
    codec_payload_offset: list[int]
    codec_type: list[UEVirtualTextureCodec]

    @classmethod
    def from_buffer(cls, buffer: Buffer, layer_count: int):
        size_in_bytes = buffer.read_uint32()
        codec_payload_size = buffer.read_uint32()
        codec_payload_offsets = []
        codec_types = []
        for _ in range(layer_count):
            codec_types.append(UEVirtualTextureCodec(buffer.read_uint8()))
            codec_payload_offsets.append(buffer.read_uint16())
        bulk_data = UEByteBulkData.from_buffer(buffer)
        return cls(bulk_data, size_in_bytes, codec_payload_size, codec_payload_offsets, codec_types)


@dataclass
class UETexture2DMipMap:
    cooked: bool
    data: UEByteBulkData
    size_x: int
    size_y: int
    size_z: int

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        return cls(buffer.read_uint32() != 0, UEByteBulkData.from_buffer(buffer), *buffer.read_fmt("3I"))


@dataclass
class UEVirtualTextureTileOffsetData:
    width: int
    height: int
    max_address: int
    addresses: list[int]
    offsets: list[int]

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        return cls(buffer.read_uint32(), buffer.read_uint32(), buffer.read_uint32(),
                   [buffer.read_uint32() for _ in range(buffer.read_uint32())],
                   [buffer.read_uint32() for _ in range(buffer.read_uint32())])


@dataclass
class UEVirtualTextureBuiltData:
    cooked: bool
    layer_count: int
    width_in_blocks: int
    height_in_blocks: int

    tile_size: int
    tile_border_size: int

    tile_index_per_chunk: list[int]
    tile_index_per_mip: list[int]
    tile_offset_in_chunk: list[int]

    layer_pixel_formats: list[str]

    chunks: list[VirtualTextureDataChunk]

    @classmethod
    def from_buffer(cls, buffer: Buffer, first_mip: int):
        strip_mips = first_mip > 0
        cooked = buffer.read_int32() != 0

        layer_count = buffer.read_uint32()
        width_in_blocks = buffer.read_uint32()
        height_in_blocks = buffer.read_uint32()
        tile_size = buffer.read_uint32()
        tile_border_size = buffer.read_uint32()

        tile_index_per_chunk = []
        tile_index_per_mip = []
        tile_offset_in_chunk = []

        if strip_mips:
            assert False
        else:
            mip_count = buffer.read_uint32()
            width = buffer.read_uint32()
            height = buffer.read_uint32()

            tile_index_per_chunk = [buffer.read_uint32() for _ in range(buffer.read_uint32())]
            tile_index_per_mip = [buffer.read_uint32() for _ in range(buffer.read_uint32())]
            tile_offset_in_chunk = [buffer.read_uint32() for _ in range(buffer.read_uint32())]

        layer_pf = []
        for _ in range(layer_count):
            layer_pf.append(buffer.read_ue_string())
        chunk_count = buffer.read_uint32()
        chunks = []
        for chunk in range(chunk_count):
            chunks.append(VirtualTextureDataChunk.from_buffer(buffer, layer_count))
        return cls(cooked, layer_count, width_in_blocks, height_in_blocks, tile_size, tile_border_size,
                   tile_index_per_chunk, tile_index_per_mip, tile_offset_in_chunk, layer_pf, chunks)


BITMASK_CUBEMAP = 1 << 31
BITMASK_HAS_OPT_DATA = 1 << 30
BITMASK_NUMSLICES = BITMASK_HAS_OPT_DATA - 1


@dataclass
class UETexturePlatformData:
    size_x: int
    size_y: int
    slice_count: int
    cubemap: bool
    pixel_format: str
    first_mip: int
    mips: list[UETexture2DMipMap]
    is_virtual: bool
    virtual_texture_build_data: UEVirtualTextureBuiltData | None

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        size_x, size_y, packed_data = buffer.read_fmt("3i")
        pf = buffer.read_ue_string()
        if packed_data & BITMASK_HAS_OPT_DATA:
            buffer.skip(8)
        slice_count = packed_data & BITMASK_NUMSLICES
        first_mip, mip_count = buffer.read_fmt("iI")
        mips = []
        for _ in range(mip_count):
            mips.append(UETexture2DMipMap.from_buffer(buffer))
        is_virtual = buffer.read_int32() != 0
        virtual_texture_build_data: UEVirtualTextureBuiltData | None = None
        if is_virtual:
            virtual_texture_build_data = UEVirtualTextureBuiltData.from_buffer(buffer, first_mip)
        return cls(size_x, size_y, slice_count, packed_data & BITMASK_CUBEMAP, pf, first_mip, mips, is_virtual,
                   virtual_texture_build_data)

    def get_data(self, ubulk_file: Buffer):
        if self.is_virtual:
            virtual_texture = self.virtual_texture_build_data
            chunk = virtual_texture.chunks[0]
            assert len(chunk.codec_type) == 1
            chunk_offset = 0
            full_texture = Image.new("RGBA", (self.size_x, self.size_y))
            tile_size = virtual_texture.tile_size
            border_size = virtual_texture.tile_border_size

            rows = self.size_x // tile_size
            columns = self.size_y // tile_size

            zi = ZOrderIndexer((0, rows), (0, columns))
            for row in range(rows):
                for column in range(columns):
                    tile_id = zi.zindex(row, column)
                    tile_offset = virtual_texture.tile_offset_in_chunk[tile_id]
                    if (tile_id + 1) > len(virtual_texture.tile_offset_in_chunk):
                        next_tile_offset = chunk_offset + chunk.size_in_bytes
                    else:
                        next_tile_offset = chunk_offset + virtual_texture.tile_offset_in_chunk[tile_id + 1]
                    ubulk_file.seek(chunk_offset + tile_offset)
                    data = ubulk_file.read(next_tile_offset - (chunk_offset + tile_offset))
                    if next_tile_offset - (chunk_offset + tile_offset) == 0:
                        continue
                    if UEVirtualTextureCodec.ZippedGPU == chunk.codec_type[0]:
                        data = zlib.decompress(data)
                    if virtual_texture.layer_pixel_formats[0] == "PF_DXT1":
                        tile = Image.frombytes("RGBA",
                                               (tile_size + border_size * 2,
                                                tile_size + border_size * 2),
                                               data, "bcn", (1, "DXT1"))
                    elif virtual_texture.layer_pixel_formats[0] == "PF_BC5":
                        tile = Image.frombytes("RGB",
                                               (tile_size + border_size * 2,
                                                tile_size + border_size * 2),
                                               data, "bcn", (5, "BC5"))
                    else:
                        raise NotImplementedError()
                    borderless_tile = tile.crop((border_size, border_size,
                                                 tile_size + border_size,
                                                 tile_size + border_size))
                    full_texture.paste(borderless_tile, (row * tile_size, column * tile_size,))
            return full_texture
        else:
            biggest_mip = None
            biggest_dim = 0
            for mip in self.mips:
                if max(mip.size_y, mip.size_x) > biggest_dim:
                    biggest_mip = mip
                    biggest_dim = max(mip.size_y, mip.size_x)
            bulk_data = biggest_mip.data
            if bulk_data.inline_data is not None:
                buffer = bulk_data.inline_data
            else:
                ubulk_file.seek(biggest_mip.data.offset_in_file)
                buffer = ubulk_file
            data = buffer.read(bulk_data.size_on_disk)
            dim = (biggest_mip.size_x,
                   biggest_mip.size_y)
            tile: Image.Image
            if self.pixel_format == "PF_DXT1":
                tile = Image.frombytes("RGBA",
                                       dim,
                                       data, "bcn", (1, "DXT1"))
            elif self.pixel_format == "PF_DXT5":
                tile = Image.frombytes("RGBA",
                                       dim,
                                       data, "bcn", (3, "DXT5"))
            elif self.pixel_format == "PF_BC5":
                tile = Image.frombytes("RGB", dim, data, "bcn", (5, "BC5"))
            elif self.pixel_format == "PF_G8":
                tile = Image.frombytes("L", dim, data)
            elif self.pixel_format == "PF_B8G8R8A8":
                tile = Image.frombytes("RGBA", dim, data)
                b, g, r, a = tile.split()
                tile = Image.merge("RGBA", (r, g, b, a))
            else:
                raise NotImplementedError(self.pixel_format)
            return tile


@dataclass
class UEStripDataFlags:
    global_strip_flags: int
    class_strip_flags: int

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        return cls(buffer.read_uint8(), buffer.read_uint8())

    def is_editor_data_stripped(self) -> bool:
        return (self.global_strip_flags & 1) != 0

    def is_data_stripped_for_server(self) -> bool:
        return (self.global_strip_flags & 2) != 0

    def is_class_data_stripped(self, flag: int) -> bool:
        return (self.class_strip_flags & flag) != 0


@dataclass
class Texture2D:
    base: UEObject
    flags1: UEStripDataFlags
    flags2: UEStripDataFlags
    cooked: int
    textures: list[UETexturePlatformData]

    @classmethod
    def from_buffer(cls, buffer: Buffer, name_map: list[Name], import_list: list[UEImportObject], export_size: int):
        base = UEObject.from_buffer(buffer, name_map, import_list, "Texture2D")
        flags1 = UEStripDataFlags.from_buffer(buffer)
        flags2 = UEStripDataFlags.from_buffer(buffer)
        cooked = buffer.read_uint32()
        textures = []
        if cooked == 1:
            pixel_format = read_name(buffer, name_map)
            while pixel_format != "None":
                skip_offset = buffer.read_int64()
                texture = UETexturePlatformData.from_buffer(buffer)
                textures.append(texture)
                pixel_format = read_name(buffer, name_map)

        return cls(base, flags1, flags2, cooked, textures)
