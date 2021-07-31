"""
Game by megat69.
"""
from ursina import *
from ursina.shaders import lit_with_shadows_shader, ssao_shader, fxaa_shader
import json
from pypresence import Presence
from map_generator import generate_map
from random import randint

################################################### INIT ###############################################################

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

# Loads the save info
with open("save.json", "r", encoding="utf-8") as f:
    save_info = json.load(f)

# Creates the Ursina app
app = Ursina(fullscreen=settings["fullscreen"], vsync=GRAPHICS["vsync"])
# Tweaks some settings
window.exit_button.visible = False
if CUSTOMIZATION_SETTINGS["FPS_counter_visible"] is True:
    window.fps_counter.color = color.lime
    window.fps_counter.y += 0.015
else:
    window.fps_counter.visible = False
window.exit_button.disabled = True
application.development_mode = True
camera.shader = fxaa_shader if GRAPHICS["FXAA_antialiasing"] is True else None

# Caps the framerate if wanted
if settings["framerate_cap"] is not None:
    from panda3d.core import ClockObject
    globalClock.setMode(ClockObject.MLimited)
    globalClock.setFrameRate(settings["framerate_cap"])

# Prepares Rich Presence
if RICH_PRESENCE_ENABLED is True:
    try:
        RPC = Presence("869880277386792960")
        RPC.connect()
        RPC_update_cooldown = 0
    except Exception as e:
        RICH_PRESENCE_ENABLED = False
        print("Rich Presence has been disabled, since the following error occurred :", e)

# Prepares intro music
if save_info["current_chapter"] == "01":
    intro_music = Audio("assets/music/intro_music.mp3", autoplay=False)

#################################################### MAIN ##############################################################
class FirstPersonController(Entity):
    def __init__(self):
        if CUSTOMIZATION_SETTINGS["crosshair_enabled"]:
            self.cursor = Entity(parent=camera.ui, model='assets/crosshair.obj',
                                 color=color.rgb(*CUSTOMIZATION_SETTINGS["crosshair_RGBA"]),
                                 scale=0.008)
        super().__init__()
        self.speed = 5
        self.height = 2
        self.camera_pivot = Entity(parent=self, y=self.height)

        camera.parent = self.camera_pivot
        camera.position = (0,0,0)
        camera.rotation = (0,0,0)
        camera.fov = GRAPHICS["FOV"]
        mouse.locked = True
        if USING_CONTROLLER is False:
            self.mouse_sensitivity = Vec2(CONTROLS["sensitivity"], CONTROLS["sensitivity"])
        self.is_crouched = False
        self.is_sprinting = False

        # Character model
        self.arms = Entity(parent=self, model="assets/Character.obj", position=(0, -3.2, -0.1),
                           texture="assets/Character_texture.png", shader=lit_with_shadows_shader)

        self.gravity = 0
        invoke(setattr, self, "gravity", 1, delay=1.4)
        self.grounded = True
        self.jump_height = 2
        self.jump_duration = .5
        self.jumping = False
        self.air_time = 0
        self.movement_allowed = True
        self.sprinting_speed = 8
        self.walking_speed = 5
        self.crouched_speed = 2

        self.inventory = []
        self.inventory_display = []
        self.title_message = Text("", y=-0.4, font="assets/font/orwell/Orwell.ttf")

        self.footstep_sounds = [Audio(f"assets/sfx/footsteps/wood/wood_footstep_sound_{i}.mp3",
                                      autoplay=False) for i in range(6)]
        self.footstep_cooldown = 5 - self.speed // 2

    def add_to_inventory(self, item):
        self.inventory.append(item)

        # Deletes everything from inventory
        for entity in self.inventory_display:
            destroy(entity)
        self.inventory_display.clear()

        # Adds items to inventory on screen
        for i, item in enumerate(self.inventory):
            self.inventory_display.append(
                Entity(parent=camera.ui, model="quad", texture=f"assets/icons/inventory/{item}.png",
                       scale=0.15, position=(-0.8, 0.42 - (0.15 * i)))
            )


    def update(self):
        if self.movement_allowed is True:
            # Crouching
            if held_keys[CONTROLS["crouch"]] and CONTROLS["hold_crouch_and_sprint"] is True:
                self.toggle_crouch_stance(True)
            elif CONTROLS["hold_crouch_and_sprint"] is True:
                self.toggle_crouch_stance(False)

            # Running
            if held_keys[CONTROLS["run"]] and CONTROLS["hold_crouch_and_sprint"] is True \
                    and self.speed != self.crouched_speed:
                self.speed = self.sprinting_speed
            elif CONTROLS["hold_crouch_and_sprint"] is True and not held_keys[CONTROLS["crouch"]]:
                self.speed = self.walking_speed

            self.footstep_cooldown -= time.dt
            if (held_keys[CONTROLS["forward"]] or held_keys[CONTROLS["backward"]] or held_keys[CONTROLS["right"]]\
                or held_keys[CONTROLS["left"]]) and self.footstep_cooldown <= 0 and self.grounded is True:
                self.footstep_sounds[randint(0, len(self.footstep_sounds) - 1)].play()
                self.footstep_cooldown = (10 - self.speed) // 3
                if self.footstep_cooldown < 0.5:
                    self.footstep_cooldown = 0.5

            if USING_CONTROLLER is False:
                self.rotation_y += mouse.velocity[0] * self.mouse_sensitivity[1]
                self.camera_pivot.rotation_x -= mouse.velocity[1] * self.mouse_sensitivity[0]
            else:
                self.rotation_y -= held_keys["gamepad right stick x"] * time.dt * CONTROLS["sensitivity"][1] \
                                   * (-1 if CONTROLS["invert_y_axis"] is False else 1)
                self.camera_pivot.rotation_x += held_keys["gamepad right stick y"] * time.dt * CONTROLS["sensitivity"][0] \
                                                * (-1 if CONTROLS["invert_x_axis"] is False else 1)

            self.camera_pivot.rotation_x = clamp(self.camera_pivot.rotation_x, -90, 90)

            self.direction = Vec3(
                self.forward * (held_keys[CONTROLS["forward"]] - held_keys[CONTROLS["backward"]])
                + self.right * (held_keys[CONTROLS["right"]] - held_keys[CONTROLS["left"]])
                ).normalized()

            """feet_ray = raycast(self.position+Vec3(0,0.5,0), self.direction, ignore=(self, self.arms), distance=.5, debug=False)
            head_ray = raycast(self.position+Vec3(0,self.height-.1,0), self.direction, ignore=(self, self.arms), distance=.5, debug=False)
            mid_ray = raycast(self.position+Vec3(0,self.height//2,0), self.direction, ignore=(self, self.arms), distance=.5, debug=False)
            if not feet_ray.hit and not head_ray.hit and not mid_ray.hit:
                self.position += self.direction * self.speed * time.dt"""
            ray = boxcast(self.position + Vec3(0,self.height//2,0), self.direction, thickness=(0.5, self.height-0.5),
                          ignore=(self, self.arms), distance=0.25, debug=False)
            if not ray.hit:
                self.position += self.direction * self.speed * time.dt
            else:
                self.footstep_cooldown += time.dt


            if self.gravity:
                # gravity
                ray = raycast(self.world_position+(0,self.height,0), self.down, ignore=(self,))
                # ray = boxcast(self.world_position+(0,2,0), self.down, ignore=(self,))

                if ray.distance <= self.height+.1:
                    if not self.grounded:
                        self.land()
                    self.grounded = True
                    # make sure it's not a wall and that the point is not too far up
                    if ray.world_normal.y > .7 and ray.world_point.y - self.world_y < .5: # walk up slope
                        self.y = ray.world_point[1]
                    return
                else:
                    self.grounded = False

                # if not on ground and not on way up in jump, fall
                self.y -= min(self.air_time, ray.distance-.05) * time.dt * 100
                self.air_time += time.dt * .25 * self.gravity

    def toggle_crouch_stance(self, is_crouched:bool=False):
        if is_crouched is True:
            self.speed = self.crouched_speed
            self.camera_pivot.y = 1
            self.arms.y = -4.2
        else:
            self.speed = self.walking_speed
            self.camera_pivot.y = 2
            self.arms.y = -3.2

    def input(self, key):
        if key == CONTROLS["jump"]:
            self.jump()

        if key == CONTROLS["run"] and CONTROLS["hold_crouch_and_sprint"] is False:
            self.is_sprinting = not self.is_sprinting
            self.speed = self.sprinting_speed if self.is_sprinting is True else self.walking_speed
            if self.is_crouched is True:
                self.is_crouched = False
                self.toggle_crouch_stance(self.is_crouched)

        if key == CONTROLS["crouch"] and CONTROLS["hold_crouch_and_sprint"] is False:
            self.is_crouched = not self.is_crouched
            if self.is_crouched is True:
                self.is_sprinting = False
            self.toggle_crouch_stance(self.is_crouched)

    def jump(self):
        if self.grounded is False:
            return

        self.grounded = False
        self.animate_y(self.y+self.jump_height, self.jump_duration, resolution=int(1//time.dt), curve=curve.out_expo)
        invoke(self.start_fall, delay=self.jump_duration)


    def start_fall(self):
        self.y_animator.pause()
        self.jumping = False

    def land(self):
        self.air_time = 0
        self.grounded = True


    def on_enable(self):
        mouse.locked = True
        if CUSTOMIZATION_SETTINGS["crosshair_enabled"]:
            self.cursor.enabled = True


    def on_disable(self):
        mouse.locked = False
        if CUSTOMIZATION_SETTINGS["crosshair_enabled"]:
            self.cursor.enabled = False

# TODO : variable "being aimed at" for all buttons
if save_info["current_chapter"] == "01":
    class DoorCollider(Button):
        def __init__(self):
            super().__init__(parent=scene, model="cube",
                             position=(0, -1.2, 7.5), scale=(1.5, 3.8, 0.1), visible=False, color=color.black)
            self.audio_cant_open_door = Audio("assets/Chapter01/door/cant_open_door.mp3", autoplay=False, loop=False)
            self.audio_door_opening = Audio("assets/Chapter01/door/door_opening.mp3", autoplay=False, loop=False)
            self.keep_looping = True

        def update(self):
            # Ends the chapter 01
            if distance(self, player) < 1.85 and is_door_opened is True and self.keep_looping is True:
                self.keep_looping = False
                player.movement_allowed = False
                intro_music.play()
                player.inventory_display[0].animate_color(color.rgb(0, 0, 0, 0), duration=1)
                player.inventory.clear()

                title = Entity(parent=camera.ui, model="quad", texture="assets/title.png", visible=False, scale=(1.5, 0.5))
                author_name = Entity(parent=camera.ui, model="quad", texture="assets/author_name.png",
                                     visible=False, scale=(0.75, 0.25), y=-0.3)
                hider = Entity(parent=camera.ui, model="quad", color=color.black,
                                     visible=False, scale=6)
                invoke(setattr, title, "visible", True, delay=7)
                invoke(setattr, author_name, "visible", True, delay=9.6)
                invoke(setattr, author_name, "visible", False, delay=14.6)
                invoke(setattr, title, "visible", False, delay=16.9)
                invoke(setattr, hider, "visible", True, delay=19.3)
                invoke(intro_music.stop, delay=23.5)
                # TODO fade out : intro_music.fade_out(duration=0.7, delay=23.5)
                # TODO : Make the player rotate towards the door completely

        def input(self, key):
            if self.hovered:
                global is_door_opened
                # If we try to open the door
                if key == CONTROLS["interact"] and distance(self, player) < 4 and is_door_opened is False:
                    print("Trying to open the door.")
                    # If the player has no key : can't open door
                    if not "key" in player.inventory:
                        self.audio_cant_open_door.play()
                    # Can open door
                    else:
                        self.audio_door_opening.play()
                        invoke(setattr, self, "visible", True, delay=0.8)
                        door.animate_rotation((0, 90, 0), duration=self.audio_door_opening.length - 1)
                        door.animate_position(door.position+Vec3(-0.7, 0, -0.7), duration=self.audio_door_opening.length - 1)
                        door.collider = "mesh"
                        is_door_opened = True

        def on_mouse_enter(self):
            if distance(self, player) < 4 and is_door_opened is False:
                if not "key" in player.inventory:
                    player.title_message.text = "This door is locked."
                else:
                    player.title_message.text = dedent(f"(<lime>{CONTROLS['interact'].upper()}<default>) Open the door")
                player.title_message.x = -0.12

        def on_mouse_exit(self):
            player.title_message.text = ""
            player.title_message.x = 0

    class Paper(Button):
        def __init__(self):
            super().__init__(parent=scene, model="plane", scale=0.2,
                             position=(0, -2.98, 0), color=color.white)

        def on_mouse_enter(self):
            if distance(self, player) < 2:
                player.title_message.text = "The key is on the chandelier."
                player.title_message.x = -0.18

        def on_mouse_exit(self):
            player.title_message.text = ""
            player.title_message.x = 0

    class Key(Button):
        def __init__(self):
            super().__init__(parent=scene, model="assets/Chapter01/key/key.obj",
                             texture="assets/Chapter01/key/key_texture.jpg",
                             position=(0, 1.1, 0), rotation=(90, 90, 0), scale=0.8)
            self.audio_keys = Audio("assets/Chapter01/door/keys.mp3", autoplay=False, loop=False)

        def input(self, key):
            if self.hovered:
                # If we try to open the door
                if key == CONTROLS["interact"] and distance(self, player) < 5:
                    # Picking up key
                    self.audio_keys.play()
                    player.add_to_inventory("key")
                    player.title_message.text = ""
                    destroy(self)

        def on_mouse_enter(self):
            if distance(self, player) < 5:
                player.title_message.text = dedent(f"(<lime>{CONTROLS['interact'].upper()}<default>) Pickup the key")
                player.title_message.x = -0.18

        def on_mouse_exit(self):
            player.title_message.text = ""
            player.title_message.x = 0

if __name__ == "__main__":
    # Main function, gets called every frame
    def update():
        global RICH_PRESENCE_ENABLED
        global RPC_update_cooldown

        # Updates the RPC cooldown
        if RICH_PRESENCE_ENABLED is True:
            try:
                RPC_update_cooldown -= time.dt
                if RPC_update_cooldown <= 0:
                    RPC.update(
                        state="Discovering a story...",
                        details=f"Chapter 01 : Awakening",
                        start=int(time.time())
                    )
                    RPC_update_cooldown = 15
            except Exception as e:
                RICH_PRESENCE_ENABLED = False
                print("Rich Presence has been disabled, since the following error occurred :", e)

    # Creates the player
    player = FirstPersonController()
    #EditorCamera()

    # Generates the given map
    generate_map(f"assets/Chapter_{save_info['current_chapter']}_map.json", scene, player)

    if save_info["current_chapter"] == "01":
        is_door_opened = False

        # Door
        door = Entity(model="assets/Chapter01/door/door.obj", texture="assets/Chapter01/door/door_texture.jpg",
                      position=(0, -3, 7.5), shader=lit_with_shadows_shader, scale=0.6, origin_x=0)
        door_collider = DoorCollider()

        paper = Paper()
        key = Key()


    # TODO : Dynamic LODs for wall textures
    # TODO : Gamepad support

    # Runs the app
    app.run()
