import bpy
import json
import mathutils
from mathutils import Euler
import math
import os

# Base directory containing all unpacked assets (exported via UE Viewer)
base_dir = r"D:\Unity\Packages\CSXfil assets"
# Optional subdirectory under base_dir if assets reside in a specific folder
asset_sub_dir = ""
# List of JSON map files exported (contains entity definitions)
map_json = [
    r'C:\Users\Rackneh\Downloads\FModel\Output\Exports\Contractors_Showdown\Plugins\Maps\BattleRoyale\Content\Level_IslandForest\A_Dam.json',
]
# Toggles
import_static = True
import_lights = False  # enable if you want lights

static_mesh_types = ['StaticMeshComponent']
light_types = ['SpotLightComponent', 'AnimatedLightComponent', 'PointLightComponent']


def split_object_path(object_path: str) -> str:
    """
    Strip trailing package suffix from Unreal ObjectPath, e.g. '/Game/Path/Mesh.Mesh' -> '/Game/Path/Mesh'
    Uses rsplit to handle paths with multiple dots.
    """
    if isinstance(object_path, str) and "." in object_path:
        return object_path.rsplit('.', 1)[0]
    return object_path


class StaticMesh:
    def __init__(self, json_entity: dict, base_dir: str, asset_sub_dir: str = ""):
        self.entity_name = json_entity.get("Outer", "UnknownEntity")
        props = json_entity.get("Properties")
        if not props or not props.get("StaticMesh"):
            self.invalid = True
            return

        object_path = props["StaticMesh"].get("ObjectPath", "")
        if not object_path:
            self.invalid = True
            return

        objpath = split_object_path(object_path)  # '/Game/.../Mesh'
        # Remove leading slash and build file path
        rel_path = objpath.lstrip('/')  # 'Game/.../Mesh'
        # Combine base_dir, asset_sub_dir, and rel_path
        file_rel = rel_path + ".gltf"
        full_path = os.path.join(base_dir, asset_sub_dir, file_rel)
        self.import_path = os.path.normpath(full_path)
        self.invalid = not os.path.exists(self.import_path)
        if self.invalid:
            print(f"Asset not found: {self.import_path}")
            return

        # Read transforms (convert cm to m and adjust axes)
        loc = props.get("RelativeLocation", {})
        self.pos = (
            loc.get("X", 0) / 100,
            -loc.get("Y", 0) / 100,
            loc.get("Z", 0) / 100,
        )
        rot = props.get("RelativeRotation", {})
        self.rot = (
            math.radians(rot.get("Roll", 0)),
            math.radians(-rot.get("Pitch", 0)),
            math.radians(-rot.get("Yaw", 0)),
        )
        scl = props.get("RelativeScale3D", {})
        self.scale = (
            scl.get("X", 1),
            scl.get("Y", 1),
            scl.get("Z", 1),
        )

    def import_staticmesh(self, collection):
        if self.invalid:
            return None
        bpy.ops.import_scene.gltf(filepath=self.import_path)
        obj = bpy.context.object
        obj.name = self.entity_name
        obj.location = self.pos
        obj.scale = self.scale
        obj.rotation_mode = 'XYZ'
        obj.rotation_euler = Euler(self.rot, 'XYZ')
        # Move to target collection
        collection.objects.link(obj)
        bpy.context.scene.collection.objects.unlink(obj)
        print(f"Imported: {self.entity_name}")
        return obj


class GameLight:
    def __init__(self, json_entity: dict):
        self.entity_name = json_entity.get("Outer", "UnknownLight")
        self.type = json_entity.get("Type", "SpotLightComponent")
        props = json_entity.get("Properties")
        self.invalid = not props
        if self.invalid:
            return

        loc = props.get("RelativeLocation", {})
        self.pos = (
            loc.get("X", 0) / 100,
            -loc.get("Y", 0) / 100,
            loc.get("Z", 0) / 100,
        )
        rot = props.get("RelativeRotation", {})
        self.rot = (
            math.radians(rot.get("Roll", 0)),
            math.radians(-rot.get("Pitch", 0)),
            math.radians(-rot.get("Yaw", 0)),
        )
        scl = props.get("RelativeScale3D", {})
        self.scale = (
            scl.get("X", 1),
            scl.get("Y", 1),
            scl.get("Z", 1),
        )

    def import_light(self, collection):
        if self.invalid:
            return None
        lt_type = 'POINT' if 'PointLight' in self.type else 'SPOT'
        light_data = bpy.data.lights.new(self.entity_name, lt_type)
        light_obj = bpy.data.objects.new(self.entity_name, light_data)
        light_obj.location = self.pos
        light_obj.scale = self.scale
        light_obj.rotation_mode = 'XYZ'
        light_obj.rotation_euler = Euler(self.rot, 'XYZ')
        collection.objects.link(light_obj)
        print(f"Light imported: {self.entity_name}")
        return light_obj


# Main processing loop
for map_file in map_json:
    if not os.path.exists(map_file):
        print(f"Map JSON not found: {map_file}")
        continue
    json_name = os.path.splitext(os.path.basename(map_file))[0]
    coll = bpy.data.collections.new(json_name)
    bpy.context.scene.collection.children.link(coll)
    with open(map_file, 'r') as f:
        entities = json.load(f)
    for ent in entities:
        t = ent.get('Type')
        if import_static and t in static_mesh_types:
            mesh = StaticMesh(ent, base_dir, asset_sub_dir)
            mesh.import_staticmesh(coll)
        if import_lights and t in light_types:
            light = GameLight(ent)
            light.import_light(coll)
print('Import complete.')
