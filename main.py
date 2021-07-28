"""
Game by megat69.
"""
from ursina import *
import json
from pypresence import Presence
from map_generator import generate_map

################################################### INIT ###############################################################

# Loads the settings
with open("settings.json", "r", encoding="utf-8") as f:
    settings = json.load(f)
    RICH_PRESENCE_ENABLED = settings["rich_presence_enabled"]
    CUSTOMIZATION_SETTINGS = settings["customization"]
    CONTROLS = settings["controls"]
    GRAPHICS = settings["graphics"]

# Creates the Ursina app
app = Ursina(fullscreen=settings["fullscreen"], vsync=settings["vsync"])
# Tweaks some settings
window.exit_button.visible = False
if CUSTOMIZATION_SETTINGS["FPS_counter_visible"] is True:
    window.fps_counter.color = color.lime
    window.fps_counter.y += 0.015
else:
    window.fps_counter.visible = False
application.development_mode = False

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
        self.mouse_sensitivity = Vec2(settings["sensitivity"], settings["sensitivity"])

        self.gravity = 1
        self.grounded = False
        self.jump_height = 2
        self.jump_duration = .5
        self.jumping = False
        self.air_time = 0

    def update(self):
        # Running
        if held_keys[CONTROLS["run"]]:
            self.speed = 8
        else:
            self.speed = 5

        # Crouching
        if held_keys[CONTROLS["crouch"]]:
            self.camera_pivot.y = 1
            self.speed = 2
        else:
            self.camera_pivot.y = 2

        self.rotation_y += mouse.velocity[0] * self.mouse_sensitivity[1]

        self.camera_pivot.rotation_x -= mouse.velocity[1] * self.mouse_sensitivity[0]
        self.camera_pivot.rotation_x = clamp(self.camera_pivot.rotation_x, -90, 90)

        self.direction = Vec3(
            self.forward * (held_keys[CONTROLS["forward"]] - held_keys[CONTROLS["backward"]])
            + self.right * (held_keys[CONTROLS["right"]] - held_keys[CONTROLS["left"]])
            ).normalized()

        feet_ray = raycast(self.position+Vec3(0,0.5,0), self.direction, ignore=(self,), distance=.5, debug=False)
        head_ray = raycast(self.position+Vec3(0,self.height-.1,0), self.direction, ignore=(self,), distance=.5, debug=False)
        if not feet_ray.hit and not head_ray.hit:
            self.position += self.direction * self.speed * time.dt


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

    def input(self, key):
        if key == CONTROLS["jump"]:
            self.jump()

    def jump(self):
        if not self.grounded:
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
    generate_map("assets/Chapter_01_map.json", scene, player)

    # Runs the app
    app.run()
