from pathlib import Path

from asset import UEAsset
from texture_2d import Texture2D
from file_utils import FileBuffer

assets_folder = Path(r"C:\PROGTAMS\Umodel\UmodelSaved\Game")

for asset_path in assets_folder.rglob("*.uasset"):
    print(asset_path)
    with FileBuffer(asset_path) as asset_file:
        asset = UEAsset.from_buffer(asset_file)

    uexp_path = asset_path.with_suffix(".uexp")
    ubulk_path = asset_path.with_suffix(".ubulk")
    with FileBuffer(uexp_path) as uexp_file:
        asset_size = asset.total_header_size
        for exported in asset.exported_objects:
            pos = exported.serial_offset - asset_size
            uexp_file.seek(pos)
            exp_type = exported.class_index.obj_import.object_name if exported.class_index.index < 0 else exported.object_name
            if exp_type == "Texture2D":
                obj = Texture2D.from_buffer(uexp_file, asset.name_map, asset.imported_objects, asset.export_size)
                for tex_id, texture in enumerate(obj.textures):
                    with FileBuffer(ubulk_path) as ubulk_file:
                        texture_data = texture.get_data(ubulk_file)
                    if tex_id == 0 and len(obj.textures) == 1:
                        output_texture_path = asset_path.with_name(exported.object_name).with_suffix(".png")
                    else:
                        output_texture_path = asset_path.with_name(exported.object_name + f"_{tex_id}").with_suffix(
                            ".png")
                    print("Saving", output_texture_path.as_posix())
                    texture_data.save(output_texture_path)