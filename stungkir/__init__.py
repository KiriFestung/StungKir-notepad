# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""StungKir - писательский блокнот на PySide6.

Тексты лежат в ~/StungKir: каждая папка - категория, внутри текстовые файлы.
Панели выдвигаются, если подвести мышь к левому или правому краю окна.
Установка: install.sh (Debian), Flatpak, установщик для Windows - см. README.md.
Лицензия GPL-3.0-or-later. Авторы: KiriFesTung вместе с Claude (Anthropic).

Как устроен код (по папкам):
  core/   основа без окон
          config - настройки, пути, темы; textutil - слова, падежи, разметка, сравнение версий;
          storage - запись на диск, кодировки, шифрование, версии, заметки, копии;
          safety - запасной файл, аварийное сохранение, один запуск; trash - корзина на 30 дней;
          snapshots - точки возврата всего проекта; conflicts - конфликты синхронизации
  world/  мир книги
          lore - справочник; templates - шаблоны карточек; worldkit - заготовки (бестиарий, государства…);
          timeline - хронология; presence - кто в какой главе
  books/  книга наружу и внутрь
          export - PDF, Word, EPUB, текст; importers - Word, LibreOffice, RTF, FB2, EPUB, HTML, Scrivener;
          covers - обложки; preview - как увидит читатель; publish - выложить на сайт; sample - пример-проект
  text/   работа с текстом
          editor - поле текста, подсветка, заметки на полях; crutches - слова-костыли; replace - найти и
          заменить во всех главах; rhythm - ритм; speakers - кто говорит; speech - чтение вслух; deadline - дедлайн
  story/  сюжет и план
          plan - план книги; board - доска сюжета; corkboard - пробковая доска; table - таблицы
  fun/    отвлечься с пользой
          dice, dicetable - кубики и стол для бросков; roulette - рулетка вызовов (challenges_extra - ещё вызовы);
          antistress - пупырка, сад камней и прочее; artwork - рисунки; sounds, soundhelper - звуки
  ui/     окна
          style, icons, dialogs, widgets - оформление, значки, диалоги и виджеты (ими пользуются все папки);
          colors - «Цвета и темы»; windows - статистика, сборка, настройки, версии;
          files, search, world, markup, panels, progress, security, project - части главного окна;
          window - главное окно целиком, собирает всё вместе
  app     запуск
  tests/  автотесты: python3 -m stungkir --test
"""

__version__ = "1.2.0"
BUILD = "2026-11-01.1"          # номер сборки: видно, какая именно версия стоит
AUTHORS = "KiriFesTung, вместе с Claude (Anthropic)"
LICENSE = "GPL-3.0-or-later"
COPYRIGHT = "Copyright (C) 2026 KiriFesTung"
