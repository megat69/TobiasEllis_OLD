from ursina import *
from ursina.shaders import lit_with_shadows_shader
import json

def generate_map(file, scene, player=None):
    """
    Generates a map for an Ursina scene from a file.
    :param file: The JSON file containing the map.
    :param scene: The Ursina scene.
    :param player: The player.
    """
    with open(file, "r", encoding="utf-8") as map_file:
        map_data = json.load(map_file)

    # Modifying player data
    if "player" in map_data and player is not None:
        for element in map_data["player"]:
            if isinstance(element, list): element = tuple(element)

            setattr(player, element, map_data["player"][element])

    # Adding the meshes to the map
    for mesh_name in map_data["meshes"]:
        mesh = map_data["meshes"][mesh_name]
        data = mesh["data"]

        # Changing some values as required
        for key in data:
            # Lists become tuple
            if isinstance(data[key], list):
                data[key] = tuple(data[key])
            # Colors become... Well, real colors.
            if key == "color":
                if data[key]["type"].lower() == "rgb":
                    data[key] = color.rgb(*data[key]["value"])
                elif data[key]["type"].lower() == "hsv":
                    data[key] = color.color(*data[key]["value"])
                else:
                    raise Exception("Color format not supported !")
            elif key == "shader" and mesh["type"] == "entity":
                data[key] = lit_with_shadows_shader if data[key] is True else None

        # Building the mesh
        if mesh["type"] == "entity":
            Entity(parent=scene, **data)
        elif mesh["type"] == "DirectionalLight":
            DirectionalLight(parent=scene, **data)
        elif mesh["type"] == "AmbientLight":
            AmbientLight(parent=scene, **data)
        else:
            raise Exception("Mesh type not supported.")