from dataclasses import dataclass
from uuid import UUID

from file_utils import Buffer


@dataclass
class CustomVersion:
    key: UUID
    version: int

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        return cls(UUID(bytes=buffer.read(16)), buffer.read_uint32())
