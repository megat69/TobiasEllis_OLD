from ursina import *
from ursina.shaders import lit_with_shadows_shader
import json

# Loads the settings
with open("settings.json", "r", encoding="utf-8") as f:
    settings = json.load(f)
    RICH_PRESENCE_ENABLED = settings["rich_presence_enabled"]
    CUSTOMIZATION_SETTINGS = settings["customization"]
    # Getting controls settings and choosing the correct one
    CONTROLS = settings["controls"]
    USING_CONTROLLER = CONTROLS["use_controller"]
    CONTROLS = CONTROLS["mouse_and_keyboard"] if USING_CONTROLLER is False else CONTROLS["controller"]
    GRAPHICS = settings["graphics"]

# Loads the translation
with open(f"assets/translation_{settings['language']}.json", "r", encoding="utf-8") as f:
    TRANSLATION = json.load(f)

# Loads the save info
with open("save.json", "r", encoding="utf-8") as f:
    save_info = json.load(f)

class LoredObject(Button):
    def __init__(self, player, object_lore:str="", distance_to_entity:(int, float)=5, **kwargs):
        super().__init__(**kwargs)
        # Loading object translation if necessary
        if object_lore.startswith("TRANSLATION->"):
            object_lore = object_lore.replace("TRANSLATION->", "", 1)
            try:
                object_lore = TRANSLATION["Chapter" + save_info["current_chapter"]][object_lore]
            except Exception as e:
                print("\n"*4 + f"Missing translation for {object_lore} (Chapter "
                               f"{save_info['current_chapter']}) in lang {settings['language']}.")
                raise e

        self.object_lore = dedent(object_lore)
        self.distance_to_entity = distance_to_entity
        self.being_aimed_at = False
        self.player = player

    def update(self):
        # On player looking
        if self.being_aimed_at is True:
            if distance(self, self.player) < self.distance_to_entity:
                self.player.title_message.text = self.object_lore
                self.player.title_message.origin = (0,0)

    def on_mouse_enter(self):
        self.being_aimed_at = True

    def on_mouse_exit(self):
        self.being_aimed_at = False
        self.player.title_message.text = ""
        self.player.title_message.x = 0

class LightIndicator(Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.blink_cooldown = 1

    def update(self):
        self.blink_cooldown -= time.dt
        if self.blink_cooldown <= 0:
            self.animate_color(color.white, duration=0.8)
            invoke(self.animate_color, color.black, duration=0.2, delay=0.8)
            self.blink_cooldown = 1

def generate_map(file, scene, player=None, debug:bool=False):
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

    map_entities = {}
    if debug is True:
        debug_entities = []

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
            if key in ("color", "pressed_color", "highlight_color"):
                if isinstance(data[key], str):
                    data[key] = getattr(color, data[key])
                elif data[key]["type"].lower() == "rgb":
                    data[key] = color.rgb(*data[key]["value"])
                elif data[key]["type"].lower() == "rgba":
                    data[key] = color.rgba(*data[key]["value"])
                elif data[key]["type"].lower() == "hsv":
                    data[key] = color.color(*data[key]["value"])
                else:
                    raise Exception("Color format not supported !")
            if key == "shader" and mesh["type"] in ("entity", "LoredObject"):
                print(mesh_name, data[key])
                data[key] = lit_with_shadows_shader if data[key] is True else None

        # Building the mesh
        if mesh["type"] == "entity":
            map_entities[mesh_name] = Entity(parent=scene, **data)
        elif mesh["type"] == "DirectionalLight":
            map_entities[mesh_name] = DirectionalLight(parent=scene, **data)
        elif mesh["type"] == "AmbientLight":
            map_entities[mesh_name] = AmbientLight(parent=scene, **data)
        elif mesh["type"] == "SpotLight":
            map_entities[mesh_name] = SpotLight(parent=scene, **data)
        elif mesh["type"] == "PointLight":
            map_entities[mesh_name] = PointLight(parent=scene, **data)
        elif mesh["type"] == "LoredObject":
            try:
                map_entities[mesh_name] = LoredObject(player, object_lore=mesh["object_lore"],
                            distance_to_entity=mesh["distance_to_entity"], parent=scene, **data)
            except Exception as e:
                print(mesh)
                raise e
        else:
            raise Exception("Mesh type not supported.")

        if "light" in mesh["type"].lower() and debug is True:
            debug_entities.append(LightIndicator(parent=scene, position=data["position"], rotation=data["rotation"],
                                                 model="assets/icons/Low_Poly_Light_Bulb.fbx", scale=1.5))

    return map_entities
