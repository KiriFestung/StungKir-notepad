# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Монетка-чеканка из рисунка KiriFesTung (packaging/art-src/coin-*.png): золото выпуклое - рельеф
по рисунку, поле - индиго-эмаль, свет и отражения настоящие (студийная HDRI с Poly Haven, hdri.py). Запуск для обеих сторон:
blender -b -P packaging/blender/coin.py -- packaging/art-src/coin-heads.png stungkir/art/coin-heads.png
blender -b -P packaging/blender/coin.py -- packaging/art-src/coin-tails.png stungkir/art/coin-tails.png figure
(figure - фигура в индиго тоже выпуклая, как ласка на решке)."""
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = argv[0], argv[1]
MODE = argv[2] if len(argv) > 2 else ""                   # figure - ласка на решке тоже выпуклая
N = 512

bpy.ops.wm.read_factory_settings(use_empty=True)
img = bpy.data.images.load(SRC)
px = np.array(img.pixels[:]).reshape(N, N, 4)          # снизу вверх, 0..1
r, g, b, a = px[..., 0], px[..., 1], px[..., 2], px[..., 3]
gold = ((r - b) > 0.18).astype(float) * (a > 0.5)


def blur(x, s):
    f = np.fft.fftfreq(N)
    fx, fy = np.meshgrid(f, f)
    return np.real(np.fft.ifft2(np.fft.fft2(x) * np.exp(-2 * (np.pi * s) ** 2 * (fx ** 2 + fy ** 2))))


yy, xx = np.mgrid[0:N, 0:N]
radius = np.hypot(xx - N / 2, yy - N / 2) / (N / 2)
figure = gold.copy()
if MODE == "figure":
    figure = np.maximum(figure, ((b > r) & (a > 0.5) & (radius < 0.84) & ((r + g + b) / 3 < 0.5)) * 0.85)
height = np.clip(blur(figure, 2.6), 0, 1) ** 0.7              # мягкий скат края, как у чеканки
# цвет без нарисованных бликов: золото - ровное, индиго - ровное, мелочь (глаз) - как в рисунке
light = (r + g + b) / 3
base = px.copy()
base[..., :3] = np.where(base[..., :3] <= 0.04045, base[..., :3] / 12.92, ((base[..., :3] + 0.055) / 1.055) ** 2.4)
gold_c = np.array([1.0, 0.58, 0.11, 1])                     # уже линейные
indigo_c = np.array([0.018, 0.012, 0.13, 1])
is_indigo = (b > r) & (a > 0.5)
base[gold > 0.5] = gold_c
base[is_indigo & (light < 0.45)] = indigo_c
for name, data in (("height", np.dstack([height, height, height, np.ones_like(height)])), ("base", base),
                   ("metal", np.dstack([gold, gold, gold, np.ones_like(gold)])), ("alpha", np.dstack([a, a, a, np.ones_like(a)]))):
    im = bpy.data.images.new(name, N, N, alpha=True, float_buffer=True)
    im.colorspace_settings.name = "Non-Color"
    im.pixels.foreach_set(data.astype(np.float32).ravel())     # цвет - до пикселей, иначе сотрёт
    im.pack()

# сетка: плоскость с плотной сеткой, рельеф - модификатором
bpy.ops.mesh.primitive_grid_add(x_subdivisions=600, y_subdivisions=600, size=2)
coin = bpy.context.object
tex = bpy.data.textures.new("h", "IMAGE")
tex.image = bpy.data.images["height"]
tex.extension = "EXTEND"
disp = coin.modifiers.new("relief", "DISPLACE")
disp.texture = tex
disp.texture_coords = "UV"
disp.strength = 0.05
disp.mid_level = 0
bpy.ops.object.shade_smooth()

mat = bpy.data.materials.new("coin")
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
uv = nt.nodes.new("ShaderNodeTexCoord")


def image_node(name):
    node = nt.nodes.new("ShaderNodeTexImage")
    node.image = bpy.data.images[name]
    node.interpolation = "Cubic"
    nt.links.new(uv.outputs["UV"], node.inputs["Vector"])
    return node


nt.links.new(image_node("base").outputs["Color"], bsdf.inputs["Base Color"])
metal = image_node("metal")
nt.links.new(metal.outputs["Color"], bsdf.inputs["Metallic"])
rough = nt.nodes.new("ShaderNodeMapRange")                  # золото 0.28, эмаль 0.12 (гладкая)
rough.inputs["To Min"].default_value = 0.12
rough.inputs["To Max"].default_value = 0.3
nt.links.new(metal.outputs["Color"], rough.inputs["Value"])
nt.links.new(rough.outputs["Result"], bsdf.inputs["Roughness"])
noise = nt.nodes.new("ShaderNodeTexNoise")                  # чуть потёртый металл
noise.inputs["Scale"].default_value = 180
bump = nt.nodes.new("ShaderNodeBump")
bump.inputs["Strength"].default_value = 0.012
nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
bsdf.inputs["Coat Weight"].default_value = 0.2
bsdf.inputs["Coat Roughness"].default_value = 0.08
alpha = image_node("alpha")
nt.links.new(alpha.outputs["Color"], bsdf.inputs["Alpha"])
coin.data.materials.append(mat)

sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.samples = 160
sc.cycles.use_denoising = True
sc.render.film_transparent = True
sc.render.resolution_x = sc.render.resolution_y = N
sc.view_settings.view_transform = "Standard"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdri  # noqa: E402

studio = hdri.world("studio_small_09", 1.6)                  # настоящая студия: блики софтбоксов по ободу и скатам
studio.node_tree.nodes["Mapping"].inputs["Rotation"].default_value[0] = math.radians(-30)   # софтбоксы - чуть над монетой


def light(name, loc, energy, size, color=(1, 1, 1)):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.size, data.color = energy, size, color
    obj = bpy.data.objects.new(name, data)
    obj.location = loc
    obj.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(obj)


light("key", (-3, 3, 4), 270, 2.0, (1, 0.95, 0.88))       # тёплый ключ слева сверху - тени рельефа
cam = bpy.data.cameras.new("c")
cam.type = "ORTHO"
cam.ortho_scale = 2.0
co = bpy.data.objects.new("c", cam)
co.location = (0, 0, 5)
sc.collection.objects.link(co)
sc.camera = co
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
