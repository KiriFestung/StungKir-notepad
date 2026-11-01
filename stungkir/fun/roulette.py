# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Русская рулетка для писателя: барабан на шесть гнёзд, в нём от одного до шести «патронов».
Крутишь, жмёшь на спуск: щёлк - пронесло, бах - выпадает писательский вызов (встроенный или свой).
Вызовы - шесть ступеней жёсткости, от безобидных до «Без тормозов» (самые чёрные - про жестокость
и грязь на странице, не в жизни)."""

import math
import random

from PySide6.QtCore import QEasingCurve, QElapsedTimer, QPointF, QRectF, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QWidget

from ..ui.dialogs import Sheet

CHAMBERS = 6

# уровень: (название, вызовы). Внутри текста - только короткое тире
LEVEL_CHALLENGES = {
    1: ("Безобидные", [
        "Добавь в сцену запах",
        "Добавь в сцену звук, который никто из героев не замечает",
        "Найди в последнем абзаце самое скучное слово и замени",
        "Опиши руки персонажа, который сейчас в кадре",
        "Закончи главу вопросом",
        "Дай персонажу привычку - мелкую, но заметную",
        "Положи в сцену предмет, который потом пригодится",
        "Перепиши первую фразу главы трижды и оставь лучшую",
        "Три вещи, которые герой видит прямо сейчас - вставь одну",
        "Пусть кто-то в сцене ест или пьёт",
        "Добавь погоду, которая мешает героям",
        "Напиши одну фразу, которую хочется процитировать",
        "Дай второстепенному персонажу имя и одну черту",
        "Абзац только из коротких предложений",
        "Придумай главе название, если его ещё нет",
        "Добавь в сцену цвет, который потом повторится",
        "Опиши, как пахнет дом персонажа",
        "Пусть персонаж что-нибудь уронит",
        "Допиши 100 слов, прежде чем встать",
        "Перечитай последнюю страницу вслух",
    ]),
    2: ("Посерьёзнее", [
        "Следующая сцена - без единой реплики",
        "Следующая сцена - только диалог",
        "Убери из последнего абзаца все прилагательные",
        "Допиши 300 слов, прежде чем встать",
        "Дай второстепенному персонажу тайну",
        "Начни следующую сцену с середины действия",
        "Опиши место глазами того, кто его ненавидит",
        "Пусть персонаж соврёт - так, чтобы читатель заметил",
        "15 минут по таймеру, телефон - в другую комнату",
        "Перескажи одну сцену глазами другого персонажа",
        "Пусть герой ошибётся и не узнает об этом",
        "Найди своё слово-паразит и убери его из главы везде",
        "Сцена, где двое хотят разного и оба правы",
        "Пусть персонаж скажет не то, что думает, а читатель поймёт",
        "Поставь сцене срок: что-то должно случиться до заката",
        "Напиши абзац без буквы «о»",
        "Перепиши последнюю реплику так, чтобы в ней был подтекст",
        "Пусть союзник героя на минуту станет помехой",
        "Опиши боль, ни разу не написав слово «боль»",
        "Вычеркни самое красивое предложение главы - если без него не хуже, так и оставь",
    ]),
    3: ("Жёсткие", [
        "10 минут пиши не останавливаясь - никаких правок",
        "Отними у героя то, на что он рассчитывал",
        "Сократи последнюю сцену на треть",
        "Убей второстепенного персонажа. Или почти",
        "Допиши 1000 слов сегодня",
        "Сцена от лица злодея - и чтобы он был прав",
        "Раскрой тайну на главу раньше, чем собирался",
        "Пусть герой проиграет спор, который должен был выиграть",
        "Перенеси сцену в другое место, перепиши и оставь лучшую",
        "Забери у героя единственный путь к отступлению",
        "Пусть самый спокойный персонаж сорвётся",
        "Сцена, где никто не говорит правду",
        "Убери из главы все наречия на «-о» - до единого",
        "Предательство от того, от кого не ждали",
        "Напиши сцену, которую боишься писать, - черновиком, без правок",
        "30 минут по таймеру без интернета",
        "Герой должен выбрать между двумя людьми - и выбрать",
        "Пусть секрет героя узнает худший из возможных людей",
        "Перепиши конец главы так, чтобы стало хуже",
        "Сцена, где герою стыдно за себя",
    ]),
    4: ("Злые", [
        "Убей персонажа, которого любишь сам",
        "Удали последнюю сцену и напиши заново, не подглядывая",
        "Допиши 2000 слов, прежде чем лечь спать",
        "Пусть герой сделает непростительное - и не пожалеет",
        "Сожги герою дом. Буквально или нет - решай сам",
        "Пусть план героя сработает - и окажется ошибкой",
        "Отдай злодею победу в этой главе",
        "Глава, где у героя нет ни одного союзника",
        "Пусть любимец читателей предаст героя",
        "Сократи главу вдвое",
        "Час письма без остановки, правки - завтра",
        "Отними у героя здоровье: рана, болезнь, увечье - и с этим жить дальше",
        "Пусть невинный пострадает из-за решения героя",
        "Пусть герой узнает, что во всём виноват он сам",
        "Напиши сцену похорон",
        "Выкинь свой лучший диалог и напиши хуже, но честнее",
        "Перепиши первую главу с нуля, не открывая старую",
        "Пусть мечта героя сбудется и сломает ему жизнь",
        "Герой остаётся один. Совсем",
        "Пусть смерть персонажа ничего не изменит - и это самое страшное",
    ]),
    5: ("Адище", [
        "Убей главного героя. Дальше решай, как жить книге",
        "Выкинь главную сюжетную линию и посмотри, что осталось",
        "Удали главу целиком. Версия сохранится - но пиши её заново",
        "Допиши 5000 слов за день",
        "Перепиши всю главу от лица злодея",
        "Пусть злодей победит окончательно - а книга продолжится",
        "Сделай героя тем, против кого он боролся",
        "Отними у героя всех, кто ему дорог. Кроме одного",
        "Пиши, пока не кончится глава. Без перерывов",
        "Напиши финал книги сегодня, даже если до него далеко",
        "Сотри любимую сцену и напиши лучше, не подглядывая",
        "Пусть всё, во что верил герой, окажется ложью",
        "Герой проиграл. Глава о том, что после",
        "Перепиши первую строчку книги 20 раз",
        "Убей рассказчика",
        "Сожги мир книги до основания - город, страну, всё, что есть",
        "Три часа без интернета и телефона. Только текст",
        "Перепиши лучшую главу хуже - и найди, на чём она держалась",
        "Пусть герой своими руками погубит того, кого любит",
        "Начни книгу заново с другим героем - хотя бы первую страницу",
    ]),
}
from .challenges_extra import MORE  # noqa: E402 - ещё по сорок на ступень и шестая, самая чёрная
from ..core.i18n import tr

for _level, _items in MORE.items():
    if _level in LEVEL_CHALLENGES:
        LEVEL_CHALLENGES[_level][1].extend(_items)
LEVEL_CHALLENGES[6] = ("Без тормозов", list(MORE[6]))
CHALLENGES = [text for _title, items in LEVEL_CHALLENGES.values() for text in items]
# что выбрать в «Вызовы»: 0 - любые; 1..6 - этот уровень и на ступень мягче, чтобы не было однообразно
LEVELS = [(0, "Любые")] + [(level, f"{level}. {title}") for level, (title, _items) in LEVEL_CHALLENGES.items()]

# сколько заряжено
LOADS = [("1", "1 патрон", 1), ("2", "2 патрона", 2), ("3", "3 патрона", 3), ("4", "4 патрона", 4),
         ("5", "5 патронов", 5), ("6", "6 - полный барабан", 6)]


def own_list(text):
    return [line.strip() for line in (text or "").split("\n") if line.strip()]


def level_pool(level):
    if not level:                                # «любые» - без шестой ступени: её выбирают нарочно
        return [text for lvl, (_t, items) in LEVEL_CHALLENGES.items() if lvl < 6 for text in items]
    pool = list(LEVEL_CHALLENGES[level][1])
    if level > 1:
        pool += LEVEL_CHALLENGES[level - 1][1]
    return pool


class Roulette:
    """Логика без рисования: что в каком гнезде, какое под курком, какой шанс вызова.
    Гнёзда: "live" - патрон (вызов), "empty" - пусто."""

    def __init__(self, rng=random, load="1"):
        self.rng = rng
        self.set_load(load)

    def set_load(self, load):
        self.load = load if load in {key for key, *_ in LOADS} else "1"
        self.reload()

    def count(self):
        return next(live for key, _title, live in LOADS if key == self.load)

    def reload(self):
        live = self.count()
        self.chambers = ["live"] * live + ["empty"] * (CHAMBERS - live)
        self.rng.shuffle(self.chambers)
        self.current = self.rng.randrange(CHAMBERS)
        self.pulled = 0                            # сколько раз щёлкнуло с последней прокрутки

    def spin(self):
        self.current = self.rng.randrange(CHAMBERS)
        self.pulled = 0
        return self.current

    @property
    def bullet(self):
        """Первое гнездо с патроном (для старых проверок и рисунка)."""
        return self.chambers.index("live") if "live" in self.chambers else None

    def chance(self):
        """(живых патронов, из скольки гнёзд) на этом нажатии: после прокрутки - из шести,
        каждый пустой щелчок без прокрутки убирает одно гнездо."""
        return self.chambers.count("live"), CHAMBERS - self.pulled

    def chance_text(self):
        live, out_of = self.chance()
        if live >= out_of:
            return "вызов будет точно"
        return f"шанс вызова {live} из {out_of}"

    def pull(self):
        """"live" - бах, вызов (после него барабан перезаряжается); "empty" - щёлк,
        барабан встаёт на следующее гнездо."""
        if self.chambers[self.current] == "live":
            return "live"
        self.current = (self.current + 1) % CHAMBERS
        self.pulled += 1
        return "empty"

    def challenge(self, own=None, only_own=False, level=0):
        own = list(own or [])
        pool = own if only_own and own else own + level_pool(level)
        return self.rng.choice(pool)


class Revolver(QWidget):
    """Барабан сверху: шесть гнёзд, под курком (вверху) - стрелка. Крутится с замедлением."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(190, 190)
        self.angle = 0.0                           # поворот барабана в градусах
        self.flash = 0.0                           # вспышка после «баха», 1 → 0
        self.shown = [None] * CHAMBERS             # что видно в гнёздах: пока не выстрелил - ничего
        self.spin_anim = QVariantAnimation(self)
        self.spin_anim.valueChanged.connect(self._turn)
        self._on_done = None
        self.spin_anim.finished.connect(lambda: self._on_done() if self._on_done else None)
        self.flash_anim = QVariantAnimation(self)
        self.flash_anim.setDuration(900)
        self.flash_anim.setStartValue(1.0)
        self.flash_anim.setEndValue(0.0)
        self.flash_anim.valueChanged.connect(self._flash)
        self.loading = None                        # (гнёзда с патронами, 0..1) - идёт зарядка
        self.on_round = None                       # патрон вошёл в гнездо - звук
        self.load_anim = QVariantAnimation(self)
        self.load_anim.setStartValue(0.0)
        self.load_anim.setEndValue(1.0)
        self.load_anim.valueChanged.connect(self._load_step)
        self._load_done = None
        self.load_anim.finished.connect(self._load_finished)
        # нарисованные кадры: «бах» (art/anim/bang) и пыль из гнезда при щелчке (art/anim/dust)
        self.effect = None                         # (имя, кадров, номер кадра)
        self.effect_clock = QElapsedTimer()
        self.effect_timer = QTimer(self, interval=16, timerType=Qt.PreciseTimer)
        self.effect_timer.timeout.connect(self._effect_step)
        self.material = "metal"                    # барабан - металлический (дуб и кость ему не идут)

    EFFECT_FPS = 30
    EFFECTS = {"bang": "anim/bang/bang", "dust": "anim/dust/dust", "glint": "anim/roulette/drum-glint"}
    DRUMS = {"bone": "drum-bone", "metal": "drum-metal", "oak": "drum-oak", "resin": "drum-indigo"}

    def play_effect(self, name):
        """Проиграть кадры поверх барабана. Нет кадров - False (тогда рисуется простая вспышка)."""
        from .artwork import frame_count
        count = frame_count(self.EFFECTS[name])
        if not count:
            return False
        self.effect = (name, count, 0)
        self.effect_clock.start()
        self.effect_timer.start()
        self.update()
        return True

    def _effect_step(self):
        if self.effect is None:
            self.effect_timer.stop()
            return
        name, count, _frame = self.effect
        frame = int(self.effect_clock.elapsed() / 1000 * self.EFFECT_FPS)
        self.effect = None if frame >= count else (name, count, frame)
        if self.effect is None:
            self.effect_timer.stop()
        self.update()

    def puff(self):
        """Щёлк вхолостую: облачко пыли из гнезда под курком."""
        self.play_effect("dust")

    def _turn(self, value):
        self.angle = float(value)
        self.update()

    def _flash(self, value):
        self.flash = float(value)
        self.update()

    @property
    def busy(self):
        return QVariantAnimation.Running in (self.spin_anim.state(), self.load_anim.state())

    # ---- зарядка: патроны по одному влетают в гнёзда, барабан защёлкивается ----
    LOAD_ROUND_MS, LOAD_TAIL_MS = 260, 420

    def load(self, chambers, on_done=None):
        rounds = [i for i, kind in enumerate(chambers) if kind == "live"]
        self.hide_all()
        self.loading = (rounds, 0.0, 0)
        self._load_done = on_done
        self.load_anim.stop()
        self.load_anim.setDuration(self.LOAD_ROUND_MS * len(rounds) + self.LOAD_TAIL_MS)
        self.load_anim.start()

    def _load_phase(self, value):
        """(сколько патронов уже в гнёздах, прогресс текущего 0..1, прозрачность в конце 1..0)."""
        rounds = self.loading[0]
        total = self.LOAD_ROUND_MS * len(rounds) + self.LOAD_TAIL_MS
        ms = value * total
        inside = min(len(rounds), int(ms // self.LOAD_ROUND_MS))
        current = (ms % self.LOAD_ROUND_MS) / self.LOAD_ROUND_MS if inside < len(rounds) else 1.0
        tail = max(0.0, ms - self.LOAD_ROUND_MS * len(rounds)) / self.LOAD_TAIL_MS
        fade = 1.0 if tail < 0.45 else max(0.0, 1 - (tail - 0.45) / 0.55)
        return inside, current, fade

    def _load_step(self, value):
        if self.loading is None:
            return
        rounds, _old, heard = self.loading
        inside, _current, _fade = self._load_phase(float(value))
        while heard < inside:                      # каждый вошедший патрон - щелчок
            heard += 1
            if self.on_round:
                self.on_round(heard == len(rounds))
        self.loading = (rounds, float(value), heard)
        self.update()

    def _load_finished(self):
        self.loading = None
        self.play_effect("glint")                  # барабан защёлкнулся - блик по металлу
        self.update()
        done, self._load_done = self._load_done, None
        if done:
            done()

    def finish_load(self):
        if self.load_anim.state() == QVariantAnimation.Running:
            self.load_anim.setCurrentTime(self.load_anim.duration())

    def turn_to(self, chamber, turns=0, duration=300, on_done=None):
        """Повернуть так, чтобы гнездо chamber встало под курок (+ полные обороты для прокрутки).
        Барабан всегда крутится в одну сторону, как настоящий."""
        target = -chamber * 360 / CHAMBERS
        end = self.angle - (self.angle - target) % 360 - 360 * turns
        self.spin_anim.stop()
        self._on_done = on_done
        self.spin_anim.setStartValue(self.angle)
        self.spin_anim.setEndValue(end)
        self.spin_anim.setDuration(duration if end != self.angle else 1)
        self.spin_anim.setEasingCurve(QEasingCurve.OutCubic if turns else QEasingCurve.OutBack)
        self.spin_anim.start()

    def finish(self):
        self.finish_load()                         # зарядка кончилась - следом может начаться прокрутка
        if self.spin_anim.state() == QVariantAnimation.Running:
            self.spin_anim.setCurrentTime(self.spin_anim.duration())

    @property
    def revealed(self):
        return any(kind in ("live", "blank") for kind in self.shown)

    def hide_all(self):
        self.shown = [None] * CHAMBERS
        self.update()

    def boom(self, chambers, strength=1.0):
        """Бах: показать, что было в барабане (после патрона - всё; после холостого - только его гильзу)."""
        self.shown = list(chambers)
        if not self.play_effect("bang"):                # нет нарисованных кадров - простая вспышка
            self.flash_anim.setStartValue(float(strength))
            self.flash_anim.start()

    def mark(self, index, kind):
        self.shown[index] = kind
        self.update()

    def _cartridge(self, p, spot, hole, kind):
        """Что видно в гнезде: латунный патрон с капсюлем, серебристый холостой со звёздочкой-обжимом,
        стреляная гильза (пробитый капсюль) или просто темнота."""
        p.setPen(QPen(QColor("#1b1d21"), 2))
        if kind not in ("live", "blank", "spent"):
            p.setBrush(QColor("#0c0d0f"))
            p.drawEllipse(spot, hole, hole)
            return
        metal = QRadialGradient(spot - QPointF(hole * 0.3, hole * 0.3), hole * 1.2)
        if kind == "live":
            metal.setColorAt(0, QColor("#ffe08a"))
            metal.setColorAt(1, QColor("#b8862b"))
        else:
            metal.setColorAt(0, QColor("#f2f4f7"))
            metal.setColorAt(1, QColor("#8a9099"))
        p.setBrush(metal)
        p.drawEllipse(spot, hole, hole)
        if kind == "live":                                       # капсюль
            p.setBrush(QColor("#c9a14a"))
            p.setPen(QPen(QColor("#8a6a22"), 1))
            p.drawEllipse(spot, hole * 0.35, hole * 0.35)
        elif kind == "blank":                                    # холостой: обжатый «звёздочкой» нос
            p.setPen(QPen(QColor("#5d636c"), 1.4))
            for k in range(6):
                a = math.pi * k / 3
                p.drawLine(spot, spot + QPointF(math.cos(a), math.sin(a)) * hole * 0.6)
        else:                                                    # стреляный: капсюль пробит
            p.setBrush(QColor("#3a3d42"))
            p.setPen(Qt.NoPen)
            p.drawEllipse(spot, hole * 0.35, hole * 0.35)
            p.setBrush(QColor("#111214"))
            p.drawEllipse(spot, hole * 0.12, hole * 0.12)

    def _paint_loading(self, p, radius, hole):
        """Зарядка (рисуется в повёрнутых координатах барабана): патроны по одному влетают в гнёзда снаружи."""
        from .artwork import scaled
        rounds, value, _heard = self.loading
        inside, current, fade = self._load_phase(value)
        base = scaled("round-live", 2 * hole, self.devicePixelRatioF())
        p.save()
        p.setOpacity(fade)
        for k, i in enumerate(rounds):
            if k > inside:
                break
            a = math.radians(i * 360 / CHAMBERS - 90)          # рисуем уже в повёрнутых координатах барабана
            home = QPointF(math.cos(a), math.sin(a)) * radius * 0.59
            if k == inside:                                   # летит: из-за края барабана, с замедлением
                ease = 1 - (1 - current) ** 3
                start = home * 2.1
                spot = start + (home - start) * ease
                size = hole * (1.35 - 0.35 * ease)
            else:
                spot, size = home, hole
            if base.isNull():
                self._cartridge(p, spot, size, "live")
            else:
                p.drawPixmap(QRectF(spot.x() - size, spot.y() - size, 2 * size, 2 * size), base,
                             QRectF(base.rect()))
        p.restore()

    def _paint_steel(self, p, center, radius):
        """Запасной барабан, нарисованный кодом (если картинки нет)."""
        steel = QRadialGradient(center - QPointF(radius * 0.3, radius * 0.4), radius * 1.3)
        steel.setColorAt(0, QColor("#9aa0aa"))
        steel.setColorAt(0.6, QColor("#4b5058"))
        steel.setColorAt(1, QColor("#25282d"))
        p.setPen(QPen(QColor("#15171a"), 2))
        p.setBrush(steel)
        p.drawEllipse(center, radius, radius)
        # желобки между гнёздами и сами гнёзда - поворачиваются вместе с барабаном
        for i in range(CHAMBERS):
            a = math.radians(self.angle + i * 360 / CHAMBERS - 90)
            spot = center + QPointF(math.cos(a), math.sin(a)) * radius * 0.56
            groove = center + QPointF(math.cos(a + math.pi / CHAMBERS), math.sin(a + math.pi / CHAMBERS)) * radius * 0.9
            p.setPen(QPen(QColor(20, 22, 26, 140), 3))
            p.drawLine(groove, groove + QPointF(math.cos(a + math.pi / CHAMBERS),
                                                math.sin(a + math.pi / CHAMBERS)) * radius * 0.08)
            self._cartridge(p, spot, radius * 0.22, self.shown[i])
        p.setPen(QPen(QColor("#1b1d21"), 2))
        p.setBrush(QColor("#6b7079"))
        p.drawEllipse(center, radius * 0.13, radius * 0.13)              # ось

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        side = min(self.width(), self.height()) - 16
        center = QPointF(self.width() / 2, self.height() / 2 + 6)
        radius = side / 2 - 4
        if self.flash > 0:                                               # вспышка «баха»
            glow = QRadialGradient(center, radius * 1.4)
            color = QColor("#ffb347")
            color.setAlphaF(0.55 * self.flash)
            glow.setColorAt(0, color)
            color.setAlphaF(0.0)
            glow.setColorAt(1, color)
            p.setPen(Qt.NoPen)
            p.setBrush(glow)
            p.drawEllipse(center, radius * 1.4, radius * 1.4)
        from .artwork import scaled
        drum = scaled(self.DRUMS.get(self.material, "drum"), 2 * radius, self.devicePixelRatioF())
        if drum.isNull():
            drum = scaled("drum", 2 * radius, self.devicePixelRatioF())
        if not drum.isNull():
            # нарисованный барабан (индиго с охрой) и патроны в гнёздах крутятся как одна вещь:
            # раньше патроны рисовались поверх неповёрнутыми, и казалось, что они «плывут» по барабану
            p.setRenderHint(QPainter.SmoothPixmapTransform)
            p.save()
            p.translate(center)
            p.rotate(self.angle)
            p.drawPixmap(QRectF(-radius, -radius, 2 * radius, 2 * radius), drum, QRectF(drum.rect()))
            hole = radius * 0.205
            for i in range(CHAMBERS):
                kind = self.shown[i]
                if kind not in ("live", "blank", "spent"):
                    continue
                a = math.radians(i * 360 / CHAMBERS - 90)
                spot = QPointF(math.cos(a), math.sin(a)) * radius * 0.59
                base = scaled(f"round-{kind}", 2 * hole, self.devicePixelRatioF())
                p.drawPixmap(QRectF(spot.x() - hole, spot.y() - hole, 2 * hole, 2 * hole), base, QRectF(base.rect()))
            if self.loading is not None:
                self._paint_loading(p, radius, hole)
            p.restore()
        else:
            self._paint_steel(p, center, radius)
        # курок сверху: стрелка цвета «Важное»
        tip = center - QPointF(0, radius * 1.02)
        p.setPen(QPen(QColor("#2e2a6e"), 1.6))
        p.setBrush(QColor("#d4a02e"))
        size = radius * 0.12
        p.drawPolygon([tip + QPointF(0, size), tip + QPointF(-size, -size), tip + QPointF(size, -size)])
        if self.effect is not None:
            name, _count, frame = self.effect
            if name == "bang":                           # «бах» - на весь барабан
                spot, extent = center, radius + 6
            elif name == "glint":                        # блик - ровно по барабану
                spot, extent = center, radius
            else:                                        # пыль - из гнезда под курком
                spot, extent = center - QPointF(0, radius * 0.59), radius * 0.62
            picture = scaled(f"{self.EFFECTS[name]}_{frame:02d}", 2 * extent, self.devicePixelRatioF())
            if not picture.isNull():
                p.setRenderHint(QPainter.SmoothPixmapTransform)
                p.drawPixmap(QRectF(spot.x() - extent, spot.y() - extent, 2 * extent, 2 * extent), picture,
                             QRectF(picture.rect()))
        p.end()


class OwnChallengesDialog(Sheet):
    """Свои вызовы: каждый с новой строки. Выпадают вместе со встроенными или только они."""

    def __init__(self, parent, text, only_own):
        super().__init__(parent, tr("Свои вызовы"))
        self.setMinimumWidth(640)
        hint = QLabel(tr("Каждый вызов - с новой строки. Например: «Сцена в темноте - только звуки и запахи»."))
        hint.setObjectName("Status")
        hint.setWordWrap(True)
        self.content.addWidget(hint)
        self.edit = QPlainTextEdit()
        self.edit.setPlainText(text)
        self.edit.setPlaceholderText(tr("Напиши свои вызовы здесь…"))
        self.edit.setMinimumHeight(220)
        self.content.addWidget(self.edit, 1)
        self.only = QCheckBox(tr("Только свои - встроенные не выпадают"))
        self.only.setChecked(only_own)
        self.content.addWidget(self.only)
        row = QHBoxLayout()
        builtin = QPushButton(tr("Вставить встроенные"))
        builtin.setToolTip(tr("Встроенные вызовы допишутся в список: лишние удали, остальные поправь, "
                           "и поставь галочку «Только свои»"))
        builtin.clicked.connect(self._insert_builtin)
        row.addWidget(builtin)
        row.addStretch()
        cancel = QPushButton(tr("Отмена"))
        cancel.clicked.connect(self.reject)
        ok = QPushButton(tr("Сохранить"))
        ok.setObjectName("Primary")
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(ok)
        self.content.addLayout(row)

    def _insert_builtin(self):
        present = set(own_list(self.edit.toPlainText()))
        missing = [c for c in CHALLENGES if c not in present]
        if missing:
            text = self.edit.toPlainText().rstrip("\n")
            self.edit.setPlainText((text + "\n" if text else "") + "\n".join(missing))

    def text(self):
        return "\n".join(own_list(self.edit.toPlainText()))

    def only_own(self):
        return self.only.isChecked()

    def summary(self):
        count = len(own_list(self.edit.toPlainText()))
        if not count:
            return "Своих вызовов нет - выпадают встроенные"
        if self.only_own():
            return f"Выпадают только твои вызовы ({count})"
        return f"Твои вызовы ({count}) выпадают вместе со встроенными ({len(CHALLENGES)})"
