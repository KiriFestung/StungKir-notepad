# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Английский пример-проект: то же, что в sample.py, для тех, кто выбрал английский интерфейс.
Имена - те же нейтральные (Tervena, Davn, Kev, Loss)."""

BOOK = "Sample · Fog over the River"
WORLD = "Sample · World"
README_NAME = "Read me.txt"
CHAPTER_1_NAME = "Chapter 1.txt"
CHAPTER_2_NAME = "Chapter 2.txt"
BOARD_NAME = "Plot.board"
TIMELINE_NAME = "Timeline.timeline"

README = """# Read me
This is a practice book. You can touch everything here: edit, move, delete. When you are done - «More → Files and import → Remove sample», and it goes to the trash.
Move the mouse to the left edge of the window - chapters, search, modes and the «More» menu are there.
A line of dialogue starts with a dash and gets its own color:
— Like this, - said Tervena.
Hover over Tervena, Davn or Kev: these are terms from the «Sample · World» reference, each has a description. Ctrl+click opens it on the side.
[a note to myself - stays out of the book] This is what square brackets look like. The list of all such places across chapters is the «Marks» button on the left.
*Italic* and **bold** - with asterisks; the built book has no asterisks.
Open «Plot» - a story board on a corkboard: cards, pins and threads. The «Columns» switch at the top stacks them.
«Timeline» - world events by year in its own calendar.
F8 - focus mode, F9 - typewriter, F10 - no distractions, F1 - all keys.
"""

CHAPTER_1 = """# Chapter 1
The morning was dull. Tervena stood at the window and watched the fog settle on the river and hide the far bank.
— There will be no boat, - she said. - Not today.
The innkeeper shrugged and went back to the hearth. The bells were already ringing in Davn [check how many], and *nobody* expected **guests** from the south.
— And if the fog lifts by noon?
— It won't. It stays until spring.
She put on her cloak, checked the knife at her belt and stepped out onto the wet boards of the pier.
"""

CHAPTER_2 = """# Chapter 2
The envoy of Kev came in the evening. He was silent for a long time, warmed his hands by the fire and looked at the map as if he could move the mountains with his eyes.
— They will close the pass in a week, - he said at last.
— Then we will go in a week and a day, - Tervena answered.
The envoy smiled but did not argue.
* * *
That night it began to snow.
"""

WORLD_NOTES = {
    "Tervena": "Also: the Tervenan Republic\nA coastal state in the south. Its capital is *Loss*. It lives by trading salt and fish.",
    "Davn": "A mountain land of twelve clans. The bells ring when the pass closes.",
    "Kev": "A small principality in the foothills. Its envoys are careful and rarely speak first.",
}

PLAN = {
    "mode": "free",
    "columns": [
        {"title": "Setup", "cards": [
            {"id": "s1", "title": "Fog over the river", "text": "There will be no boat. Tervena decides to go alone.",
             "color": "purple", "chapter": f"{BOOK}/{CHAPTER_1_NAME}", "x": 60, "y": 60},
            {"id": "s2", "title": "The envoy of Kev", "text": "Warns about the pass.", "color": "amber",
             "chapter": f"{BOOK}/{CHAPTER_2_NAME}", "x": 360, "y": 40}]},
        {"title": "Rising action", "cards": [
            {"id": "s3", "title": "The pass", "text": "Snow, the clans of Davn, strange tracks.", "color": "green",
             "x": 660, "y": 80},
            {"id": "s4", "title": "Who knew in advance?", "text": "Someone on the council knew about the fog.",
             "color": "coral", "x": 330, "y": 260}]},
        {"title": "Resolution", "cards": [
            {"id": "s5", "title": "The last bridge", "text": "Everything will be decided on the river.", "color": "purple",
             "x": 640, "y": 300}]},
    ],
    "links": [["s1", "s4"], ["s2", "s4"], ["s4", "s5"]],
}

TIMELINE = {"events": [
    {"when": "312, Second Era", "year": 312, "title": "Loss is founded", "text": "Fishermen build the first pier.",
     "color": "none"},
    {"when": "Winter 590", "year": 590, "title": "The pass is closed for a year", "text": "Davn and Tervena do not trade.",
     "color": "coral"},
    {"when": "Autumn 614", "year": 614, "title": "Fog over the river", "text": "The book begins.", "color": "purple",
     "chapter": f"{BOOK}/{CHAPTER_1_NAME}"},
]}
