from dataclasses import dataclass

from file_utils import Buffer


@dataclass
class EngineVersion:
    major: int
    minor: int
    patch: int
    build: int
    branch: str | None

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        return cls(*buffer.read_fmt("3HI"), buffer.read_ue_string())
