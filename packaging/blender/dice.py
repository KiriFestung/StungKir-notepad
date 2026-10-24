"""Кубики в Blender с нуля: d6 из кости. Запуск:
blender -b -P packaging/blender/dice.py -- <куда> [размер] [кадров]
Один кадр - картинка для кнопки (<куда>.png), несколько - кубик поворачивается вокруг себя
(<куда>_00.png ...). Нужен Blender 4.2 с blender.org: в сборках Ubuntu нет шумодава (OpenImageDenoise)."""

import math
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "/tmp/d6"
SIZE = int(argv[1]) if len(argv) > 1 else 512
FRAMES = int(argv[2]) if len(argv) > 2 else 1

BONE = (0.78, 0.74, 0.62, 1)       # кость: тёплый кремовый
PIP = (0.08, 0.06, 0.36, 1)        # лунки: индиго


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def material(name, color, rough, sss=0.0, metal=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if sss:
        bsdf.inputs["Subsurface Weight"].default_value = sss
        bsdf.inputs["Subsurface Radius"].default_value = (0.3, 0.2, 0.12)
        bsdf.inputs["Subsurface Scale"].default_value = 0.08
    bsdf.inputs["Coat Weight"].default_value = 0.25
    bsdf.inputs["Coat Roughness"].default_value = 0.2
    return mat


# лунки на гранях: (x, y) в долях половины грани
LAYOUT = {
    1: [(0, 0)],
    2: [(-1, 1), (1, -1)],
    3: [(-1, 1), (0, 0), (1, -1)],
    4: [(-1, -1), (-1, 1), (1, -1), (1, 1)],
    5: [(-1, -1), (-1, 1), (0, 0), (1, -1), (1, 1)],
    6: [(-1, -1), (-1, 0), (-1, 1), (1, -1), (1, 0), (1, 1)],
}
# грань -> (нормаль, ось «x» на грани, ось «y» на грани); напротив - в сумме 7
FACES = {
    6: ((0, -1, 0), (1, 0, 0), (0, 0, 1)),     # к камере
    1: ((0, 1, 0), (-1, 0, 0), (0, 0, 1)),
    4: ((-1, 0, 0), (0, -1, 0), (0, 0, 1)),    # слева
    3: ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    2: ((0, 0, 1), (1, 0, 0), (0, 1, 0)),
    5: ((0, 0, -1), (1, 0, 0), (0, -1, 0)),
}


def die():
    bpy.ops.mesh.primitive_cube_add(size=2)
    body = bpy.context.object
    body.name = "d6"
    bevel = body.modifiers.new("bevel", "BEVEL")
    bevel.width = 0.2
    bevel.segments = 10
    bevel.limit_method = "NONE"
    bpy.ops.object.modifier_apply(modifier="bevel")
    body.data.materials.append(material("bone", BONE, 0.38, sss=0.25))
    cutters = []
    step, radius, depth = 0.52, 0.2, 0.08
    centres = []
    for value, (normal, ax, ay) in FACES.items():
        n, ax, ay = Vector(normal), Vector(ax), Vector(ay)
        for x, y in LAYOUT[value]:
            centre = n * (1 + radius - depth) + ax * (x * step) + ay * (y * step)
            centres.append(centre)
            bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=centre, segments=64, ring_count=32)
            cutters.append(bpy.context.object)
    bpy.ops.object.select_all(action="DESELECT")
    for cutter in cutters:
        cutter.select_set(True)
    bpy.context.view_layer.objects.active = cutters[0]
    bpy.ops.object.join()
    holes = bpy.context.object
    cut = body.modifiers.new("pips", "BOOLEAN")
    cut.operation = "DIFFERENCE"
    cut.solver = "EXACT"
    cut.object = holes
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.modifier_apply(modifier="pips")
    bpy.data.objects.remove(holes)
    # лунки - индиго: грани, что легли внутрь сфер-резцов
    body.data.materials.append(material("pip", PIP, 0.45))
    verts = body.data.vertices
    for poly in body.data.polygons:
        points = [verts[i].co for i in poly.vertices]
        if any(all((p - c).length < radius + 0.002 for p in points) for c in centres):
            poly.material_index = 1
    body.rotation_euler = (math.radians(4), math.radians(-5), 0)      # чуть завален, как брошенный
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))     # край лунки - резкий, скругления - мягкие
    return body


def light(name, kind, location, energy, size, color=(1, 1, 1), shadow=True):
    data = bpy.data.lights.new(name, kind)
    data.use_shadow = shadow
    data.energy = energy
    data.color = color
    if kind == "AREA":
        data.size = size
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    obj.rotation_euler = (Vector((0, 0, 0)) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.collection.objects.link(obj)


def clean(path):
    """Почти прозрачный шум (после шумодава) - в ноль: в программе он лёг бы серой дымкой до края кадра."""
    import numpy
    image = bpy.data.images.load(path)
    pixels = numpy.array(image.pixels[:]).reshape(-1, 4)
    pixels[pixels[:, 3] < 0.06] = 0
    image.pixels[:] = pixels.ravel()
    image.filepath_raw = path
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)


def scene(body):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 96
    sc.cycles.use_denoising = True
    sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = SIZE
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    sc.render.fps = 30
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.03, 0.03, 0.08, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    sc.world = world
    light("key", "AREA", (-4, -6, 6), 520, 2.5)                        # слева сверху и спереди: тень уходит за кубик
    light("fill", "AREA", (5, -3, 1), 70, 5, (0.8, 0.82, 1.0), shadow=False)
    light("rim", "AREA", (1, 5, 4), 160, 3, shadow=False)
    # тень на невидимый стол
    bpy.ops.mesh.primitive_circle_add(radius=1.9, vertices=96, fill_type="NGON", location=(0, 0, -1))   # тень не доходит до краёв кадра
    bpy.context.object.is_shadow_catcher = True
    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = 85
    cam_data.dof.use_dof = True        # дальняя грань чуть мягче, как у фото
    cam_data.dof.aperture_fstop = 4
    cam_data.dof.focus_distance = 8.2 if FRAMES > 1 else 6.9
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.collection.objects.link(cam)
    angle = math.radians(-28)                                       # видна левая грань
    distance = 9.2 if FRAMES > 1 else 7.9                           # вращаясь, кубик шире - нужен запас
    cam.location = (math.sin(angle) * distance, -math.cos(angle) * distance, 0.5)
    cam.rotation_euler = (Vector((0, 0, 0)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    if FRAMES > 1:
        sc.frame_start, sc.frame_end = 0, FRAMES - 1
        body.rotation_euler = (0, 0, 0)
        body.keyframe_insert("rotation_euler", frame=0)
        body.rotation_euler = (0, 0, math.radians(360))
        body.keyframe_insert("rotation_euler", frame=FRAMES)
        for curve in body.animation_data.action.fcurves:
            for point in curve.keyframe_points:
                point.interpolation = "LINEAR"
        sc.render.filepath = OUT + "_##"
        bpy.ops.render.render(animation=True)
        for frame in range(FRAMES):
            clean(f"{OUT}_{frame:02d}.png")
    else:
        sc.render.filepath = OUT + ".png"
        bpy.ops.render.render(write_still=True)
        clean(OUT + ".png")


clear()
scene(die())
