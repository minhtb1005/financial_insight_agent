"""Phase 0a technical slice for the Tier 3 Blender -> Remotion pipeline.

Builds a deliberately simple procedural scene (no external assets):
  - Trau Ti (brown body/head, cream horns, blue glasses, flower, notebook)
  - a stylised Lan mannequin placeholder
  - a desk/room set with phone, envelope and shopping bag
  - 1080x1920, 30 fps, 360 frames (12 s), one camera move
  - 12 s of idle/talk/wave/point animation

Usage (from anywhere):
  blender --background --factory-startup --python p0_slice.py -- --mode render --engine EEVEE

Modes: render (PNG sequence), stills (3 PNGs), save (.blend only).
This is a technical slice, not production art.
"""

import argparse
import math
import os
import sys
import time

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
TRAU_DIR = os.path.abspath(os.path.join(HERE, "..", ".."))
DEFAULT_OUT = os.path.join(TRAU_DIR, "out")

FPS = 30
FRAMES = 360
WIDTH = 1080
HEIGHT = 1920


# ---------------------------------------------------------------- helpers
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_mat(name, color, rough=0.55, metallic=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    # Workbench fallback uses viewport display colour.
    m.diffuse_color = (*color, 1.0)
    return m


def set_mat(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    return obj


def sphere(name, loc, scale, mat, segments=24, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments, ring_count=rings, radius=1.0, location=loc
    )
    ob = bpy.context.object
    ob.name = name
    ob.scale = scale
    set_mat(ob, mat)
    return ob


def cube(name, loc, scale, mat, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rotation)
    ob = bpy.context.object
    ob.name = name
    ob.scale = scale
    set_mat(ob, mat)
    return ob


def cylinder(name, loc, radius, depth, mat, rotation=(0, 0, 0), vertices=24):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rotation
    )
    ob = bpy.context.object
    ob.name = name
    set_mat(ob, mat)
    return ob


def cone(name, loc, r1, r2, depth, mat, rotation=(0, 0, 0), vertices=24):
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices,
        radius1=r1,
        radius2=r2,
        depth=depth,
        location=loc,
        rotation=rotation,
    )
    ob = bpy.context.object
    ob.name = name
    set_mat(ob, mat)
    return ob


def torus(name, loc, major, minor, mat, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major,
        minor_radius=minor,
        major_segments=24,
        minor_segments=8,
        location=loc,
        rotation=rotation,
    )
    ob = bpy.context.object
    ob.name = name
    set_mat(ob, mat)
    return ob


def limb(name, p1, p2, radius, mat):
    """Cylinder from p1 to p2, origin moved to p1 so it rotates at the joint."""
    p1, p2 = Vector(p1), Vector(p2)
    direction = p2 - p1
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=16,
        radius=radius,
        depth=direction.length,
        location=(p1 + p2) / 2,
    )
    ob = bpy.context.object
    ob.name = name
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = direction.to_track_quat("Z", "Y")
    set_mat(ob, mat)
    bpy.context.scene.cursor.location = p1
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    bpy.context.scene.cursor.location = (0, 0, 0)
    return ob


def empty(name, loc):
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.empty_display_size = 0.15
    return ob


def parent_keep(child, parent):
    bpy.context.view_layer.update()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def key_rot(obj, frame, euler):
    obj.rotation_euler = euler
    obj.keyframe_insert("rotation_euler", frame=frame)


def key_loc(obj, frame, loc):
    obj.location = loc
    obj.keyframe_insert("location", frame=frame)


# ---------------------------------------------------------------- scene
def build_scene():
    reset_scene()
    scene = bpy.context.scene

    mats = {
        "brown": make_mat("TrauBrown", (0.36, 0.19, 0.09), 0.7),
        "brown_dark": make_mat("TrauBrownDark", (0.24, 0.12, 0.05), 0.7),
        "tan": make_mat("TrauTan", (0.58, 0.36, 0.19), 0.65),
        "cream": make_mat("Cream", (0.96, 0.88, 0.70), 0.5),
        "blue": make_mat("GlassesBlue", (0.10, 0.30, 0.72), 0.35, 0.15),
        "lens": make_mat("Lens", (0.55, 0.78, 0.96), 0.15),
        "black": make_mat("Black", (0.02, 0.02, 0.02), 0.4),
        "pink": make_mat("FlowerPink", (0.94, 0.44, 0.55), 0.55),
        "yellow": make_mat("FlowerYellow", (0.98, 0.77, 0.20), 0.5),
        "navy": make_mat("Notebook", (0.07, 0.11, 0.28), 0.6),
        "paper": make_mat("Paper", (0.95, 0.94, 0.88), 0.8),
        "coral": make_mat("LanTop", (0.87, 0.31, 0.26), 0.65),
        "denim": make_mat("LanPants", (0.16, 0.22, 0.38), 0.75),
        "skin": make_mat("Skin", (0.88, 0.68, 0.52), 0.6),
        "hair": make_mat("Hair", (0.14, 0.08, 0.06), 0.55),
        "wood": make_mat("Wood", (0.53, 0.32, 0.18), 0.7),
        "wood_dark": make_mat("WoodDark", (0.31, 0.17, 0.08), 0.7),
        "wall": make_mat("Wall", (0.78, 0.55, 0.36), 0.85),
        "rug": make_mat("Rug", (0.42, 0.50, 0.42), 0.9),
        "floor": make_mat("Floor", (0.60, 0.42, 0.26), 0.8),
        "phone": make_mat("Phone", (0.06, 0.07, 0.09), 0.3, 0.2),
        "bag": make_mat("Bag", (0.90, 0.66, 0.22), 0.7),
        "light_warm": make_mat("LightWarm", (1.0, 0.82, 0.55), 0.5),
        "light_cool": make_mat("LightCool", (0.70, 0.82, 1.0), 0.5),
    }

    # --- room / set -------------------------------------------------
    cube("Floor", (0, 0, -0.06), (12, 12, 0.08), mats["floor"])
    cube("BackWall", (0, 2.35, 3.0), (7, 0.08, 6.0), mats["wall"])
    cube("Rug", (0, -0.35, 0.012), (2.6, 1.7, 0.02), mats["rug"])
    cube("WallArtL", (-1.55, 2.30, 1.95), (0.55, 0.03, 0.70), mats["coral"])
    cube("WallArtR", (1.55, 2.30, 1.95), (0.55, 0.03, 0.70), mats["denim"])

    # desk
    cube("DeskTop", (0, 0.92, 0.90), (1.75, 0.75, 0.09), mats["wood"])
    for x in (-0.74, 0.74):
        for y in (0.55, 1.29):
            cube(f"DeskLeg_{x}_{y}", (x, y, 0.44), (0.08, 0.08, 0.84), mats["wood_dark"])

    # props: phone, envelope, shopping bag
    cube("Phone", (-0.35, 0.86, 0.985), (0.12, 0.015, 0.24), mats["phone"], rotation=(0.25, 0, 0.15))
    cube("PhoneScreen", (-0.35, 0.845, 0.995), (0.10, 0.005, 0.20), mats["lens"], rotation=(0.25, 0, 0.15))
    cube("Envelope", (0.02, 0.86, 0.978), (0.30, 0.19, 0.012), mats["cream"], rotation=(0, 0, -0.10))
    cube("EnvelopeFlap", (0.02, 0.90, 0.987), (0.21, 0.10, 0.004), mats["paper"], rotation=(0, 0, -0.10))
    cube("ShoppingBag", (0.48, 0.92, 1.10), (0.26, 0.15, 0.36), mats["bag"])
    torus("BagHandle", (0.48, 0.92, 1.30), 0.09, 0.014, mats["wood_dark"], rotation=(math.pi / 2, 0, 0))

    # --- Trau Ti ----------------------------------------------------
    brown, dark, tan = mats["brown"], mats["brown_dark"], mats["tan"]
    trau_root = empty("TrauRoot", (-0.9, 0.45, 0.0))
    head = empty("TrauHead", (-0.9, 0.45, 1.70))

    body = sphere("TrauBody", (-0.9, 0.45, 0.95), (0.52, 0.42, 0.62), brown)
    sphere("TrauBelly", (-0.9, 0.12, 0.90), (0.34, 0.16, 0.40), mats["cream"])
    sphere("TrauHeadMesh", (-0.9, 0.45, 1.70), (0.40, 0.36, 0.36), brown)
    sphere("TrauSnout", (-0.9, 0.10, 1.60), (0.22, 0.16, 0.13), tan)
    sphere("TrauNoseL", (-0.96, -0.05, 1.63), (0.026, 0.02, 0.024), mats["black"])
    sphere("TrauNoseR", (-0.84, -0.05, 1.63), (0.026, 0.02, 0.024), mats["black"])
    mouth = sphere("TrauMouth", (-0.9, -0.02, 1.54), (0.075, 0.018, 0.038), mats["black"])
    sphere("TrauEarL", (-1.27, 0.51, 1.64), (0.14, 0.08, 0.10), dark)
    sphere("TrauEarR", (-0.53, 0.51, 1.64), (0.14, 0.08, 0.10), dark)
    cone("TrauHornL", (-1.20, 0.44, 1.93), 0.09, 0.0, 0.34, mats["cream"], rotation=(0, -0.95, 0))
    cone("TrauHornR", (-0.60, 0.44, 1.93), 0.09, 0.0, 0.34, mats["cream"], rotation=(0, 0.95, 0))
    sphere("TrauEyeL", (-1.02, 0.10, 1.76), (0.035, 0.025, 0.035), mats["black"])
    sphere("TrauEyeR", (-0.78, 0.10, 1.76), (0.035, 0.025, 0.035), mats["black"])

    # blue round glasses
    gx = -0.9
    gy = 0.075
    gz = 1.76
    torus("GlassesL", (gx - 0.125, gy, gz), 0.105, 0.017, mats["blue"], rotation=(math.pi / 2, 0, 0))
    torus("GlassesR", (gx + 0.125, gy, gz), 0.105, 0.017, mats["blue"], rotation=(math.pi / 2, 0, 0))
    limb("GlassesBridge", (gx - 0.02, gy, gz), (gx + 0.02, gy, gz), 0.012, mats["blue"])
    limb("GlassesTempleL", (gx - 0.23, gy, gz), (gx - 0.29, 0.22, gz), 0.012, mats["blue"])
    limb("GlassesTempleR", (gx + 0.23, gy, gz), (gx + 0.29, 0.22, gz), 0.012, mats["blue"])

    # flower on head
    flower_c = (gx + 0.20, 0.12, 2.02)
    for i in range(5):
        a = i * 2 * math.pi / 5
        sphere(
            f"FlowerPetal{i}",
            (flower_c[0] + 0.065 * math.cos(a), flower_c[1] - 0.03, flower_c[2] + 0.065 * math.sin(a)),
            (0.052, 0.028, 0.052),
            mats["pink"],
        )
    sphere("FlowerCenter", flower_c, (0.048, 0.03, 0.048), mats["yellow"])

    # legs / feet
    for side, x in (("L", -1.14), ("R", -0.66)):
        cylinder(f"TrauLeg{side}", (x, 0.45, 0.21), 0.13, 0.34, dark)
        sphere(f"TrauFoot{side}", (x, 0.34, 0.07), (0.16, 0.22, 0.08), dark)

    # arms. right arm is animated on an empty pivot at the shoulder.
    right_arm = limb("TrauArmR", (-1.32, 0.45, 1.28), (-1.52, 0.28, 0.86), 0.10, brown)
    right_hand = sphere("TrauHandR", (-1.52, 0.28, 0.84), (0.11, 0.10, 0.11), tan)
    right_pivot = empty("TrauArmRPivot", (-1.32, 0.45, 1.28))
    left_arm = limb("TrauArmL", (-0.48, 0.45, 1.28), (-0.34, 0.20, 0.92), 0.10, brown)
    left_hand = sphere("TrauHandL", (-0.34, 0.20, 0.90), (0.11, 0.10, 0.11), tan)

    # notebook in the left hand
    book = cube("Notebook", (-0.30, 0.10, 1.02), (0.16, 0.025, 0.21), mats["navy"], rotation=(0.15, 0.15, 0.25))
    pages = cube("NotebookPages", (-0.30, 0.085, 1.02), (0.145, 0.012, 0.195), mats["paper"], rotation=(0.15, 0.15, 0.25))

    parent_keep(right_arm, right_pivot)
    parent_keep(right_hand, right_pivot)
    parent_keep(left_hand, left_arm)

    head_parts = [o for o in bpy.data.objects if o.name in (
        "TrauHeadMesh", "TrauSnout", "TrauNoseL", "TrauNoseR", "TrauMouth",
        "TrauEarL", "TrauEarR", "TrauHornL", "TrauHornR", "TrauEyeL", "TrauEyeR",
    ) or o.name.startswith("Glasses") or o.name.startswith("Flower")]
    root_parts = [body, bpy.data.objects["TrauBelly"], right_pivot, left_arm, book, pages]
    root_parts += [o for o in bpy.data.objects if o.name.startswith(("TrauLeg", "TrauFoot"))]
    for ob in head_parts:
        parent_keep(ob, head)
    parent_keep(head, trau_root)
    for ob in root_parts:
        parent_keep(ob, trau_root)

    # --- Lan mannequin ---------------------------------------------
    lan_root = empty("LanRoot", (0.9, 0.35, 0.0))
    skin, coral, denim = mats["skin"], mats["coral"], mats["denim"]

    sphere("LanHead", (0.9, 0.35, 1.62), (0.20, 0.19, 0.22), skin)
    sphere("LanHair", (0.9, 0.42, 1.70), (0.22, 0.20, 0.17), mats["hair"])
    sphere("LanHairBun", (0.9, 0.57, 1.82), (0.11, 0.10, 0.11), mats["hair"])
    sphere("LanEyeL", (0.83, 0.17, 1.66), (0.022, 0.014, 0.022), mats["black"])
    sphere("LanEyeR", (0.97, 0.17, 1.66), (0.022, 0.014, 0.022), mats["black"])
    sphere("LanMouth", (0.90, 0.17, 1.55), (0.045, 0.012, 0.014), mats["black"])
    cylinder("LanNeck", (0.9, 0.35, 1.42), 0.06, 0.14, skin)
    cone("LanTorso", (0.9, 0.35, 1.12), 0.17, 0.22, 0.50, coral)
    sphere("LanShoulders", (0.9, 0.35, 1.34), (0.24, 0.18, 0.10), coral)
    sphere("LanHips", (0.9, 0.35, 0.82), (0.19, 0.15, 0.13), denim)
    limb("LanArmL", (1.13, 0.35, 1.30), (1.24, 0.14, 0.92), 0.055, skin)
    lan_arm_r = limb("LanArmR", (0.67, 0.35, 1.30), (0.56, 0.14, 0.92), 0.055, skin)
    lan_arm_r_pivot = empty("LanArmRPivot", (0.67, 0.35, 1.30))
    lan_hand_l = sphere("LanHandL", (1.24, 0.14, 0.90), (0.06, 0.055, 0.06), skin)
    lan_hand_r = sphere("LanHandR", (0.56, 0.14, 0.90), (0.06, 0.055, 0.06), skin)
    for side, x in (("L", 1.02), ("R", 0.78)):
        limb(f"LanLeg{side}", (x, 0.35, 0.78), (x, 0.31, 0.08), 0.075, denim)
        sphere(f"LanFoot{side}", (x, 0.25, 0.055), (0.11, 0.17, 0.055), mats["hair"])
    for ob in bpy.data.objects:
        if ob.name.startswith("Lan") and ob not in (lan_root, lan_arm_r, lan_hand_r, lan_arm_r_pivot):
            parent_keep(ob, lan_root)
    parent_keep(lan_arm_r_pivot, lan_root)
    parent_keep(lan_arm_r, lan_arm_r_pivot)
    parent_keep(lan_hand_r, lan_arm_r_pivot)

    # --- cameras ----------------------------------------------------
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS

    target_wide = empty("CamTargetWide", (-0.10, 0.55, 1.10))
    target_trau = empty("CamTargetTrau", (-0.9, 0.45, 1.68))
    target_lan = empty("CamTargetLan", (0.9, 0.35, 1.35))

    def make_cam(name, loc, target, lens):
        data = bpy.data.cameras.new(name)
        data.lens = lens
        data.sensor_width = 36
        cam = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(cam)
        cam.location = loc
        con = cam.constraints.new("TRACK_TO")
        con.target = target
        con.track_axis = "TRACK_NEGATIVE_Z"
        con.up_axis = "UP_Y"
        return cam

    cam_wide = make_cam("CamWide", (0.15, -6.60, 2.35), target_wide, 35)
    make_cam("CamTrau", (-0.90, -2.30, 1.95), target_trau, 65)
    make_cam("CamLan", (0.90, -2.40, 1.82), target_lan, 65)
    scene.camera = cam_wide

    # one camera move: slow push-in and slight lateral drift
    key_loc(cam_wide, 1, (0.15, -6.60, 2.35))
    key_loc(cam_wide, 180, (-0.02, -6.35, 2.42))
    key_loc(cam_wide, 360, (-0.10, -6.10, 2.50))

    # --- lights -----------------------------------------------------
    def area(name, loc, energy, size, color, target):
        data = bpy.data.lights.new(name, type="AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = color
        ob = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(ob)
        ob.location = loc
        look_at(ob, target)
        return ob

    area("KeyLight", (-3.2, -3.8, 4.4), 700, 4.5, (1.0, 0.82, 0.62), (0, 0.4, 1.1))
    area("FillLight", (3.4, -2.4, 3.0), 260, 4.0, (0.72, 0.84, 1.0), (0, 0.4, 1.1))
    area("RimLight", (0.5, 2.0, 3.4), 300, 3.0, (1.0, 0.70, 0.45), (0, 0.4, 1.4))

    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("P0World")
        scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.42, 0.24, 0.13, 1.0)
    bg.inputs[1].default_value = 0.8

    # --- animation --------------------------------------------------
    # Trau Ti: subtle bob + talk mouth + wave then point.
    for f in range(1, 361, 30):
        key_rot(head, f, (0.025 * math.sin(f / 22.0), 0, 0.045 * math.sin(f / 31.0)))
        trau_root.location = (trau_root.location.x, trau_root.location.y, 0.012 * math.sin(f / 18.0))
        trau_root.keyframe_insert("location", frame=f)

    base_mouth = (0.075, 0.018, 0.038)
    for f in range(1, 361, 8):
        talking = 55 <= f <= 300
        mult = 0.55 + 0.85 * abs(math.sin(f / 7.0)) if talking else 0.6
        mouth.scale = (base_mouth[0], base_mouth[1], base_mouth[2] * mult)
        mouth.keyframe_insert("scale", frame=f)

    for f, rot in (
        (1, (0, 0, 0)),
        (60, (0, 0.35, 0)),
        (120, (0, 1.55, 0)),
        (150, (0, 1.95, 0)),
        (180, (0, 1.65, 0)),
        (210, (0, 1.95, 0)),
        (240, (0, 1.80, 0)),
        (270, (-0.95, 0.45, 0)),
        (300, (-1.05, 0.30, 0)),
        (330, (0, 0.20, 0)),
        (360, (0, 0, 0)),
    ):
        key_rot(right_pivot, f, rot)

    # Lan: idle sway + one small gesture.
    for f in range(1, 361, 30):
        lan_root.rotation_euler = (0, 0, 0.018 * math.sin(f / 34.0))
        lan_root.keyframe_insert("rotation_euler", frame=f)
        lan_root.location = (0.9, 0.35, 0.004 * math.sin(f / 21.0))
        lan_root.keyframe_insert("location", frame=f)

    for f, rot in (
        (1, (0, 0, 0)),
        (120, (0, 0, 0)),
        (180, (-0.30, 0, 0)),
        (220, (-0.52, 0, 0)),
        (260, (-0.28, 0, 0)),
        (330, (0, 0, 0)),
        (360, (0, 0, 0)),
    ):
        key_rot(lan_arm_r_pivot, f, rot)

    scene.frame_start = 1
    scene.frame_end = FRAMES
    scene.frame_set(1)

    return scene, cam_wide


# ---------------------------------------------------------------- render
def configure_engine(scene, engine, samples):
    if engine == "EEVEE":
        scene.render.engine = "BLENDER_EEVEE_NEXT"
        scene.eevee.taa_render_samples = samples
        scene.eevee.use_shadows = True
    elif engine == "CYCLES":
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = 0.05
        scene.render.use_persistent_data = True
    elif engine == "WORKBENCH":
        scene.render.engine = "BLENDER_WORKBENCH"
        shading = scene.display.shading
        shading.light = "STUDIO"
        shading.color_type = "MATERIAL"
        shading.show_shadows = True
        shading.show_cavity = True
        shading.cavity_type = "BOTH"
        shading.show_specular_highlight = True
    else:
        raise SystemExit(f"unknown engine: {engine}")

    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.compression = 15
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"

    if engine == "WORKBENCH":
        # Workbench ignores the scene lights; brighten its studio light instead.
        scene.display.shading.studio_light = "studio.sl"
        scene.display.shading.studiolight_intensity = 1.25
        scene.view_settings.view_transform = "Standard"
        scene.view_settings.exposure = 0.25


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["render", "stills", "save"], default="render")
    parser.add_argument("--engine", choices=["EEVEE", "CYCLES", "WORKBENCH"], default="EEVEE")
    parser.add_argument("--samples", type=int, default=16)
    parser.add_argument("--frames", type=int, nargs=2, default=[1, FRAMES])
    parser.add_argument("--percent", type=int, default=100)
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])

    scene, cam_wide = build_scene()
    scene.render.resolution_percentage = args.percent
    scene.frame_start, scene.frame_end = args.frames
    configure_engine(scene, args.engine, args.samples)

    os.makedirs(args.out, exist_ok=True)

    if args.mode == "save":
        path = os.path.join(args.out, "p0-slice.blend")
        bpy.ops.wm.save_as_mainfile(filepath=path)
        print(f"P0_SAVED: {path}")
        return

    if args.mode == "stills":
        stills = (
            ("CamTrau", 180, os.path.join(args.out, "p0-still-trau.png")),
            ("CamLan", 230, os.path.join(args.out, "p0-still-lan.png")),
            ("CamWide", 200, os.path.join(args.out, "p0-still-wide.png")),
        )
        for cam_name, frame, path in stills:
            scene.camera = bpy.data.objects[cam_name]
            scene.frame_set(frame)
            scene.render.filepath = path
            t0 = time.perf_counter()
            bpy.ops.render.render(write_still=True)
            print(f"P0_STILL: {path} {time.perf_counter() - t0:.2f}s")
        return

    # render mode
    seq_dir = os.path.join(args.out, f"seq-{args.engine.lower()}")
    os.makedirs(seq_dir, exist_ok=True)
    scene.camera = cam_wide
    scene.render.filepath = os.path.join(seq_dir, "frame_")
    scene.render.use_file_extension = True
    t0 = time.perf_counter()
    bpy.ops.render.render(animation=True)
    elapsed = time.perf_counter() - t0
    n = args.frames[1] - args.frames[0] + 1
    print(f"P0_RENDER_SECONDS: {elapsed:.3f}")
    print(f"P0_FRAMES: {n}")
    print(f"P0_SEC_PER_FRAME: {elapsed / n:.3f}")
    print(f"P0_SEQ_DIR: {seq_dir}")


if __name__ == "__main__":
    main()
