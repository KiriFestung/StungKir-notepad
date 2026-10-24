# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Настоящий студийный свет для сцен Blender: HDRI-карта с Poly Haven (CC0 - можно где угодно и без подписи).
Карта скачивается один раз в ~/.cache/stungkir-hdri (в репозиторий не кладётся - 6 МБ).
Металл и эмаль отражают софтбоксы студии - выглядят как на фото, а не как под одной лампой."""

import math
import urllib.request
from pathlib import Path

import bpy

CACHE = Path.home() / ".cache" / "stungkir-hdri"
URL = "https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/2k/{name}_2k.hdr"


def fetch(name):
    path = CACHE / f"{name}_2k.hdr"
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        part = path.with_suffix(".part")
        urllib.request.urlretrieve(URL.format(name=name), part)
        part.rename(path)
    return path


def world(name="studio_small_09", strength=1.0, turn=0.0, visible=False):
    """Окружение сцены - HDRI name, повёрнутое на turn градусов. visible=False - фон прозрачный
    (на картинке только предмет), но свет и отражения - от студии."""
    tree_world = bpy.data.worlds.new(name)
    tree_world.use_nodes = True
    nodes, links = tree_world.node_tree.nodes, tree_world.node_tree.links
    coords = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Rotation"].default_value = (0, 0, math.radians(turn))
    env = nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(str(fetch(name)))
    links.new(coords.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], env.inputs["Vector"])
    background = nodes["Background"]
    background.inputs["Strength"].default_value = strength
    links.new(env.outputs["Color"], background.inputs["Color"])
    scene = bpy.context.scene
    scene.world = tree_world
    scene.render.film_transparent = not visible
    return tree_world
