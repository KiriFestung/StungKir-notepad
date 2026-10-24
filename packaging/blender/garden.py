# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Сад камней и озеро в Blender с нуля: четыре камня, «блинчик» для озера и грабли. Запуск:
blender -b -P packaging/blender/garden.py -- <папка art>
Камни - сфера, смятая шумом и ячейками (как скол), материал - шум цвета, крапинки и рельеф.
Тени под камнями рисует программа, поэтому здесь их нет. Нужен Blender 4.2 с blender.org (шумодав)."""

import math
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ART = argv[0] if argv else "/tmp/art"

# камень: (форма x, y, z), (сила ячеек, сила шума), цвета (тёмный, светлый, крапинки), шероховатость, зерно
STONES = {
    1: ((1.2, 1.0, 0.75), (0.3, 0.07), ((0.22, 0.22, 0.24), (0.46, 0.45, 0.47), (0.08, 0.08, 0.09)), 0.62, 0.6),   # гранит
    2: ((1.45, 0.8, 0.5), (0.2, 0.05), ((0.12, 0.12, 0.16), (0.26, 0.26, 0.32), (0.34, 0.34, 0.38)), 0.5, 0.15),   # сланец
    3: ((1.1, 1.05, 0.8), (0.32, 0.08), ((0.40, 0.33, 0.24), (0.66, 0.58, 0.45), (0.32, 0.25, 0.17)), 0.8, 0.4),    # песчаник
    4: ((1.3, 0.88, 0.62), (0.16, 0.08), ((0.03, 0.03, 0.07), (0.10, 0.09, 0.20), (0.10, 0.09, 0.20)), 0.5, 0.0),   # индиго-базальт
}


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)


def node(tree, kind, **inputs):
    item = tree.nodes.new(kind)
    for name, value in inputs.items():
        item.inputs[name].default_value = value
    return item


def rock_material(name, colors, rough, grain, seed):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    bsdf = tree.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = rough
    coords = tree.nodes.new("ShaderNodeTexCoord")
    shift = node(tree, "ShaderNodeVectorMath")
    shift.operation = "ADD"
    shift.inputs[1].default_value = (seed * 7.1, seed * 3.3, seed * 1.9)
    tree.links.new(coords.outputs["Object"], shift.inputs[0])
    big = node(tree, "ShaderNodeTexNoise", Scale=2.2, Detail=8.0, Roughness=0.6)       # пятна тона
    tree.links.new(shift.outputs[0], big.inputs["Vector"])
    ramp = tree.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.3, 0.72
    ramp.color_ramp.elements[0].color = (*colors[0], 1)
    ramp.color_ramp.elements[1].color = (*colors[1], 1)
    tree.links.new(big.outputs["Fac"], ramp.inputs["Fac"])
    specks = node(tree, "ShaderNodeTexVoronoi", Scale=70.0, Randomness=1.0)             # крапинки зёрен
    tree.links.new(shift.outputs[0], specks.inputs["Vector"])
    speck_ramp = tree.nodes.new("ShaderNodeValToRGB")
    speck_ramp.color_ramp.elements[0].position = 0.97 - 0.12 * grain
    speck_ramp.color_ramp.elements[1].position = 0.99 - 0.1 * grain
    tree.links.new(specks.outputs["Color"], speck_ramp.inputs["Fac"])
    mix = tree.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["B"].default_value = (*colors[2], 1)
    tree.links.new(speck_ramp.outputs["Color"], mix.inputs["Factor"])
    tree.links.new(ramp.outputs["Color"], mix.inputs["A"])
    tree.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    fine = node(tree, "ShaderNodeTexNoise", Scale=60.0, Detail=10.0, Roughness=0.7)     # мелкий рельеф
    tree.links.new(shift.outputs[0], fine.inputs["Vector"])
    bump = node(tree, "ShaderNodeBump", Strength=0.3 + 0.3 * grain, Distance=0.03)
    tree.links.new(fine.outputs["Fac"], bump.inputs["Height"])
    tree.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def stone(kind):
    shape, (cells, lumps), colors, rough, grain = STONES[kind]
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=6, radius=1)
    body = bpy.context.object
    body.scale = shape
    bpy.ops.object.transform_apply(scale=True)
    for texture_kind, strength, size in (("VORONOI", cells, 0.9), ("CLOUDS", lumps, 0.6)):
        texture = bpy.data.textures.new(f"{texture_kind}{kind}", texture_kind)
        texture.noise_scale = size
        if texture_kind == "VORONOI":
            texture.distance_metric = "DISTANCE"
        displace = body.modifiers.new(texture_kind, "DISPLACE")
        displace.texture = texture
        displace.strength = strength
        displace.texture_coords = "OBJECT"
        empty = bpy.data.objects.new(f"seed{kind}{texture_kind}", None)
        empty.location = (kind * 3.7, kind * 1.3, kind * 2.1)
        bpy.context.collection.objects.link(empty)
        displace.texture_coords_object = empty
    smooth = body.modifiers.new("smooth", "SMOOTH")
    smooth.factor, smooth.iterations = 0.5, 2
    bpy.ops.object.shade_smooth()
    body.data.materials.append(rock_material(f"rock{kind}", colors, rough, grain, kind))
    body.rotation_euler = (0, 0, math.radians(kind * 23 - 30))
    return body


def skip_stone():
    """Плоская обкатанная галька: гладкая, серо-синяя, с тонкими прожилками."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=48, radius=1)
    body = bpy.context.object
    body.scale = (1.3, 1.0, 0.26)
    bpy.ops.object.transform_apply(scale=True)
    texture = bpy.data.textures.new("pebble", "CLOUDS")
    texture.noise_scale = 1.2
    displace = body.modifiers.new("lumps", "DISPLACE")
    displace.texture, displace.strength = texture, 0.04
    bpy.ops.object.shade_smooth()
    mat = rock_material("pebble", ((0.17, 0.18, 0.24), (0.42, 0.43, 0.5), (0.62, 0.62, 0.66)), 0.42, 0.1, 9)
    tree = mat.node_tree
    veins = node(tree, "ShaderNodeTexWave", Scale=1.6, Distortion=6.0, Detail=4.0)     # светлая прожилка
    ramp = tree.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.96, 0.985
    tree.links.new(veins.outputs["Fac"], ramp.inputs["Fac"])
    mix = tree.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["B"].default_value = (0.55, 0.55, 0.56, 1)
    bsdf = tree.nodes["Principled BSDF"]
    tree.links.new(bsdf.inputs["Base Color"].links[0].from_socket, mix.inputs["A"])
    tree.links.new(ramp.outputs["Color"], mix.inputs["Factor"])
    tree.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    body.data.materials.append(mat)
    body.rotation_euler = (math.radians(-8), math.radians(6), math.radians(12))
    return body


def wood_material(name, light, dark):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    bsdf = tree.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.5
    bsdf.inputs["Coat Weight"].default_value = 0.12
    coords = tree.nodes.new("ShaderNodeTexCoord")
    stretch = node(tree, "ShaderNodeMapping")
    stretch.inputs["Scale"].default_value = (1, 1, 0.08)        # волокна вдоль длинной стороны
    tree.links.new(coords.outputs["Object"], stretch.inputs["Vector"])
    rings = node(tree, "ShaderNodeTexWave", Scale=3.0, Distortion=8.0, Detail=6.0, **{"Detail Roughness": 0.7})
    rings.wave_type = "RINGS"
    tree.links.new(stretch.outputs["Vector"], rings.inputs["Vector"])
    ramp = tree.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*dark, 1)
    ramp.color_ramp.elements[1].color = (*light, 1)
    tree.links.new(rings.outputs["Fac"], ramp.inputs["Fac"])
    tree.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return mat, stretch


def rake():
    """Грабли для песка: светлый бамбук-ясень, рукоять с обмоткой индиго, латунные кольца.
    Концы зубьев - на z=0: по ним выставлено остриё курсора."""
    wood, stretch = wood_material("ash", (0.66, 0.38, 0.14), (0.36, 0.17, 0.05))
    wood_across, across = wood_material("ash-across", (0.66, 0.38, 0.14), (0.36, 0.17, 0.05))
    across.inputs["Scale"].default_value = (0.08, 1, 1)
    indigo = bpy.data.materials.new("indigo")
    indigo.use_nodes = True
    bsdf = indigo.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.06, 0.05, 0.3, 1)
    bsdf.inputs["Roughness"].default_value = 0.75
    brass = bpy.data.materials.new("brass")
    brass.use_nodes = True
    bsdf = brass.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.8, 0.55, 0.2, 1)
    bsdf.inputs["Metallic"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = 0.3

    def part(obj, mat, bevel=0.0):
        if bevel:
            mod = obj.modifiers.new("bevel", "BEVEL")
            mod.width, mod.segments = bevel, 4
        obj.data.materials.append(mat)
        bpy.ops.object.shade_smooth()
        return obj

    tines, spread = 7, 0.3
    for i in range(tines):
        x = (i - (tines - 1) / 2) * spread
        bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.06, radius2=0.095, depth=0.62, location=(x, 0, 0.31))
        part(bpy.context.object, wood)
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0.74))
    bar = bpy.context.object
    bar.scale = (spread * tines / 2 + 0.06, 0.13, 0.17)
    bpy.ops.object.transform_apply(scale=True)
    part(bar, wood_across, 0.04)
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.13, depth=2.25, location=(0, 0, 1.95))
    part(bpy.context.object, wood)
    for z in (0.9, 2.62):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.135, minor_radius=0.035, location=(0, 0, z))
        part(bpy.context.object, brass)
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.15, depth=0.42, location=(0, 0, 2.86))
    part(bpy.context.object, indigo, 0.03)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.15, location=(0, 0, 3.1))
    part(bpy.context.object, brass)
    return 3.22


def light(name, kind, location, energy, size, color=(1, 1, 1), shadow=True):
    data = bpy.data.lights.new(name, kind)
    data.use_shadow = shadow
    data.energy = energy
    data.color = color
    data.size = size
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    obj.rotation_euler = (Vector((0, 0, 0)) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.collection.objects.link(obj)


def setup(size_x, size_y):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 128
    sc.cycles.use_denoising = True
    sc.render.film_transparent = True
    sc.render.resolution_x, sc.render.resolution_y = size_x, size_y
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.5, 0.52, 0.6, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.12
    sc.world = world
    light("key", "AREA", (-5, -4, 7), 950, 3.0)                          # слева сверху - как тень в программе
    light("fill", "AREA", (6, -5, 2), 45, 6, (0.82, 0.86, 1.0), shadow=False)
    light("rim", "AREA", (2, 6, 5), 260, 3, (1.0, 0.92, 0.8), shadow=False)


def camera(elevation, scale, target=(0, 0, 0)):
    data = bpy.data.cameras.new("cam")
    data.type = "ORTHO"
    data.ortho_scale = scale
    cam = bpy.data.objects.new("cam", data)
    bpy.context.collection.objects.link(cam)
    angle = math.radians(elevation)
    cam.location = Vector(target) + Vector((0, -math.cos(angle) * 20, math.sin(angle) * 20))
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam


def clean(path):
    """Почти прозрачный шум после шумодава - в ноль, иначе в программе ляжет серой дымкой."""
    import numpy
    image = bpy.data.images.load(path)
    pixels = numpy.array(image.pixels[:]).reshape(-1, 4)
    pixels[pixels[:, 3] < 0.06] = 0
    image.pixels[:] = pixels.ravel()
    image.filepath_raw = path
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    clean(path)


for kind in STONES:
    clear()
    setup(256, 256)
    stone(kind)
    camera(58, 3.15)                          # сверху, чуть сбоку: как камень в саду
    render(f"{ART}/stone-{kind}.png")

clear()
setup(256, 112)
skip_stone()
camera(22, 2.9)
render(f"{ART}/skip-stone.png")

clear()
setup(256, 256)
height = rake()
scale = height / 0.86                        # остриё зубьев - на 112/128 высоты кадра (курсор)
camera(0, scale, (0, 0, scale * (0.5 - 16 / 128)))
render(f"{ART}/rake.png")
