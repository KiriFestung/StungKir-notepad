# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Английские надписи: русский текст из кода -> английский. Пропущенное остаётся по-русски.
Сгруппировано по файлам, где надпись встречается (первое место). Подстановки {…} - те же, что в русском;
русское в «…» и [ … ] оставлено нарочно: это примеры русского текста, с которым работает функция."""

EN = {
    # app.py
    "StungKir уже открыт.\n\nДва окна на одни и те же главы затирали бы правки друг друга, поэтому второе не открывается. Окно может быть свёрнуто или на другом рабочем столе.":
        "StungKir is already open.\n\nTwo windows on the same chapters would overwrite each other's edits, so a second one does not open. The window may be minimized or on another desktop.",
    "Не всё перенеслось из «{OLD_ROOT}» в «{ROOT}». Старая папка осталась на месте, ничего не удалено.\n\n{migration_error}":
        "Not everything moved from «{OLD_ROOT}» to «{ROOT}». The old folder stayed in place, nothing was deleted.\n\n{migration_error}",
    "Файл ключа {n} повреждён, без него зашифрованные тексты не открыть.\n\nВозьми файл ключа из последней резервной копии (архив в {BACKUP_DIR}: внутри StungKir/.stungkir/lock.json, в старых копиях - StungKir/.lock.json) и положи его на место.\n\nПодробности: {n2}":
        "The key file {n} is damaged; without it the encrypted texts cannot be opened.\n\nTake the key file from the latest backup (an archive in {BACKUP_DIR}: inside StungKir/.stungkir/lock.json, in older backups StungKir/.lock.json) and put it back.\n\nDetails: {n2}",
    "Тексты зашифрованы, а библиотеки cryptography нет.\nЗапусти install.sh ещё раз.":
        "The texts are encrypted, but the cryptography library is missing.\nRun install.sh again.",
    "Прошлый раз блокнот закрылся аварийно, но всё было сохранено":
        "Last time the notepad closed unexpectedly, but everything was saved",
    "Восстановление":
        "Recovery",
    # books/preview.py
    "Бумага книги":
        "Book paper",
    "Шелест страниц":
        "Page rustle",
    "страница {n} из {total}":
        "page {n} of {total}",
    "глава {n} из {total} · {n2}%":
        "chapter {n} of {total} · {n2}%",
    "Листай вниз колесом или перетаскиванием - следующая глава подгрузится сама":
        "Scroll down with the wheel or by dragging - the next chapter loads by itself",
    # books/publish.py
    "владелец/репозиторий, например KiriFesTung/SeMo":
        "owner/repository, for example KiriFesTung/SeMo",
    "\nНа сайт уходят только главы со статусом «Готово» (правый клик по главе → Статус). В интернет StungKir выходит только по этой кнопке.":
        "\nOnly chapters with the status «Done» go to the site (right-click a chapter → Status). StungKir goes online only with this button.",
    "Нажми «Проверить» - покажу, что изменится на сайте.":
        "Press «Check» - I will show what will change on the site.",
    "Проверить":
        "Check",
    "Выложить":
        "Publish",
    "Смотрю, что сейчас на сайте…":
        "Looking at what is on the site now…",
    "Ни одна глава не отмечена «Готово». Правый клик по главе → Статус → Готово.":
        "No chapter is marked «Done». Right-click a chapter → Status → Done.",
    "Не прочиталась глава: {error}":
        "A chapter could not be read: {error}",
    "На сайте уже всё так же, как здесь. Выкладывать нечего.":
        "The site already matches what is here. Nothing to publish.",
    "Выкладываю…":
        "Publishing…",
    "Готово! Сайт обновится сам через пару минут.":
        "Done! The site will update by itself in a couple of minutes.",
    "{result}\nНичего не изменилось - можно «Проверить» ещё раз.":
        "{result}\nNothing changed - you can «Check» again.",
    # books/sample.py
    "Пример добавлен. Убрать - «Ещё → Файлы и импорт → Убрать пример»":
        "Sample added. To remove it - «More → Files and import → Remove sample»",
    "Убрать пример в корзину? Оттуда его можно вернуть 30 дней.":
        "Move the sample to the trash? It can be restored from there for 30 days.",
    "Пример в корзине. Чистый лист!":
        "The sample is in the trash. A clean page!",
    # core/conflicts.py
    "Глава «{stem}» поменялась на двух устройствах, и программа синхронизации оставила вторую версию рядом. Здесь - {n} {n2}, в копии - {n3}. Ниже - чем копия отличается: зачёркнутого в ней нет, выделенное в ней добавлено.":
        "The chapter «{stem}» changed on two devices, and the sync program left the second version next to it. Here - {n} {n2}, in the copy - {n3}. Below is how the copy differs: crossed-out text is missing in it, highlighted text was added in it.",
    ". Что бы ни выбрал, проигравшая версия останется: копия - в корзине, твоя - в «Версиях файла».":
        ". Whatever you choose, the losing version stays: the copy goes to the trash, yours to «File versions».",
    "Оставить обе":
        "Keep both",
    "Копия станет отдельной главой «… (вторая версия)»":
        "The copy becomes a separate chapter «… (second version)»",
    "Взять ту":
        "Take that one",
    "Текст копии встанет в главу, а твой уйдёт в «Версии файла»":
        "The copy's text goes into the chapter, and yours goes to «File versions»",
    "Оставить мою":
        "Keep mine",
    "Копия уйдёт в корзину":
        "The copy goes to the trash",
    "Позже":
        "Later",
    "Конфликт синхронизации в «{stem}»{more}. Нажми сюда - разобрать":
        "Sync conflict in «{stem}»{more}. Click here to sort it out",
    "«{name}» - не текст, его не открыть. ":
        "«{name}» is not text, it cannot be opened. ",
    # core/safety.py
    "Что-то пошло не так внутри блокнота - {note}. Подробности в {name}":
        "Something went wrong inside the notepad - {note}. Details in {name}",
    "Набранное вернулось. Сохрани, если всё на месте":
        "Your typing is back. Save if everything is in place",
    "Стёрто {lost} {n}. Нажми сюда - вернуть":
        "Erased {lost} {n}. Click here to bring it back",
    "Вернул":
        "Restored",
    # core/trash.py
    "Удалённое лежит здесь {DAYS} дней, потом исчезает само. Вернулась глава - вернулись и её версии с заметками.":
        "Deleted items stay here for {DAYS} days, then disappear by themselves. When a chapter comes back, its versions and notes come back too.",
    "Очистить корзину":
        "Empty trash",
    "Удалить насовсем":
        "Delete forever",
    "Удалить насовсем? Вернуть будет нельзя.":
        "Delete forever? It cannot be restored.",
    "Удалить насовсем всё, что в корзине ({count})? Вернуть будет нельзя.":
        "Delete everything in the trash forever ({count})? It cannot be restored.",
    # fun/antistress.py
    "Новый лист":
        "New sheet",
    "Подсказка":
        "Hint",
    "Заново":
        "Again",
    "Дальше":
        "Next",
    "Разровнять":
        "Smooth out",
    "Лопнуто: {total}":
        "Popped: {total}",
    "Щёлкай по пузырькам или веди мышью с зажатой кнопкой":
        "Click the bubbles or drag the mouse with the button held",
    "{title}, уровень {level}: решено за {moves}! Жми «Дальше»":
        "{title}, level {level}: solved in {moves}! Press «Next»",
    "{title}, уровень {level} · ходов {moves} · зажги все клавиши. Клавиша переключает и соседей":
        "{title}, level {level} · moves {moves} · light up all keys. A key also flips its neighbors",
    # fun/dice.py
    "Каждый вариант - с новой строки.\nНапример: дождь\nтуман\nясно":
        "One option per line.\nFor example: rain\nfog\nclear",
    "Вычёркивать выпавшее (без повторов)":
        "Cross out what came up (no repeats)",
    "Крутани барабан и жми «Спуск»: щёлк - пронесло, бах - писательский вызов. Без прокрутки шанс с каждым щелчком растёт.":
        "Spin the cylinder and press «Trigger»: click - you got lucky, bang - a writing challenge. Without spinning, the chance grows with every click.",
    "Насколько жёсткие вызовы выпадают: от безобидных до адища":
        "How harsh the challenges are: from harmless to hellish",
    "Свои вызовы…":
        "My challenges…",
    "Крутануть барабан":
        "Spin the cylinder",
    "История":
        "History",
    "Что выпадало, пока открыт блокнот":
        "What came up while the notepad is open",
    "Открыть статью":
        "Open the article",
    "Бросить":
        "Roll",
    "Из чего:":
        "Made of:",
    "от":
        "from",
    "Заряжено:":
        "Loaded:",
    "Вызовы:":
        "Challenges:",
    "Сейчас сверху - {n}. Как в жизни: монетка чуть чаще падает той стороной, что лежала сверху (50,8 на 49,2 - опыт на 350 757 бросках), а на ребро встаёт примерно раз из 6000. Подлетит, покрутится и упадёт на стол.":
        "Now on top - {n}. Just like in real life: a coin lands slightly more often on the side that was on top (50.8 to 49.2 - an experiment with 350,757 flips), and lands on its edge about once in 6000. It flies up, spins and drops onto the table.",
    "Список пуст: впиши варианты, каждый с новой строки":
        "The list is empty: enter options, one per line",
    "Пока не из чего выбирать: добавь персонажей или справочник мира":
        "Nothing to choose from yet: add characters or a world reference",
    "Заряжено: {n}. Крутани барабан":
        "Loaded: {n}. Spin the cylinder",
    "Барабан крутится…":
        "The cylinder is spinning…",
    "Заряжаю…":
        "Loading…",
    "Жми «Спуск»: {n}":
        "Press «Trigger»: {n}",
    "Щёлк. Пронесло. Дальше: {n}":
        "Click. Lucky. Next: {n}",
    "Бах! Вот твой вызов. Барабан перезаряжен - крутани заново":
        "Bang! Here is your challenge. The cylinder is reloaded - spin again",
    "Стереть историю":
        "Clear history",
    "Пока ничего не выпадало":
        "Nothing has come up yet",
    # fun/roulette.py
    "Каждый вызов - с новой строки. Например: «Сцена в темноте - только звуки и запахи».":
        "One challenge per line. For example: «A scene in the dark - only sounds and smells».",
    "Напиши свои вызовы здесь…":
        "Write your challenges here…",
    "Только свои - встроенные не выпадают":
        "Only mine - built-in ones do not come up",
    "Вставить встроенные":
        "Insert built-in ones",
    "Встроенные вызовы допишутся в список: лишние удали, остальные поправь, и поставь галочку «Только свои»":
        "The built-in challenges are added to the list: delete the extra ones, edit the rest, and tick «Only mine»",
    # story/board.py
    "Название сцены":
        "Scene title",
    "Что происходит в сцене…":
        "What happens in the scene…",
    "Удалить карточку":
        "Delete card",
    "Перетащи, чтобы поменять колонки местами. Двойной клик - переименовать":
        "Drag to swap columns. Double-click to rename",
    "Новая карточка":
        "New card",
    "+ колонка":
        "+ column",
    "Вписать":
        "Fit",
    "Показать все карточки целиком":
        "Show all cards in full",
    "двойной клик - карточка · правый клик - нитка, цвет · Ctrl+колесо - масштаб · Shift+мышь - двигать":
        "double-click - card · right-click - thread, color · Ctrl+wheel - zoom · Shift+mouse - pan",
    "двойной клик - новая карточка или изменить; карточки и колонки (за заголовок) перетаскиваются мышкой":
        "double-click - new card or edit; cards and columns (by the header) are dragged with the mouse",
    "Новая карточка здесь":
        "New card here",
    "Вписать всё":
        "Fit all",
    "Протянуть нитку… (потом щёлкни другую карточку)":
        "Draw a thread… (then click another card)",
    "Убрать нитки":
        "Remove threads",
    "Новая колонка":
        "New column",
    "Название колонки:":
        "Column name:",
    "Колонка":
        "Column",
    "Удалить колонку":
        "Delete column",
    "Удалить колонку «{n}» вместе с карточками?":
        "Delete the column «{n}» with its cards?",
    "Сдвинуть влево":
        "Move left",
    "Сдвинуть вправо":
        "Move right",
    "Вставить колонку справа":
        "Insert column to the right",
    # story/plan.py
    "Щелчок по статусу или «Чей взгляд» - выбрать. Двойной щелчок по году или «О чём» - написать, по названию - открыть главу. Перетащи главу, чтобы поменять порядок. Год главы - в летоисчислении книги; без него возраст героев не посчитать.":
        "Click a status or «Point of view» to choose. Double-click a year or «About» to write, a title to open the chapter. Drag a chapter to change the order. The chapter year is in the book's calendar; without it the heroes' ages cannot be calculated.",
    "Из хронологии: событие, связанное с этой главой":
        "From the timeline: an event linked to this chapter",
    "Не в книгу: при сборке эта глава не отмечена":
        "Not in the book: this chapter is unchecked when building",
    "Не в книгу":
        "Not in the book",
    "Другое имя…":
        "Another name…",
    "Ничей":
        "Nobody's",
    "Чей взгляд":
        "Point of view",
    "От чьего лица «{stem}»:":
        "Whose point of view is «{stem}»:",
    "Год главы…":
        "Chapter year…",
    "О чём глава…":
        "What the chapter is about…",
    "Год - это число, например 1203 или -40":
        "A year is a number, for example 1203 or -40",
    # story/table.py
    "двойной клик по заголовку - переименовать, правый клик - ещё":
        "double-click a header to rename, right-click for more",
    "Новый столбец":
        "New column",
    "Название столбца:":
        "Column name:",
    "Удалить столбец":
        "Delete column",
    "Удалить столбец «{title}» со всеми ячейками?":
        "Delete the column «{title}» with all its cells?",
    "Столбец":
        "Column",
    "Сортировать А → Я":
        "Sort A → Z",
    "Сортировать Я → А":
        "Sort Z → A",
    "Вставить столбец слева":
        "Insert column to the left",
    "Вставить столбец справа":
        "Insert column to the right",
    "Вставить строку выше":
        "Insert row above",
    "Вставить строку ниже":
        "Insert row below",
    "Удалить строку":
        "Delete row",
    "Добавить строку":
        "Add row",
    # text/crutches.py
    "По слову или обороту в строке. Формы слова находятся сами: «вздохнул» - это и «вздохнула», и «вздохнули». Добавлять можно и из текста: правый клик по слову.":
        "One word or phrase per line. Word forms are found automatically: «вздохнул» also matches «вздохнула» and «вздохнули». You can also add from the text: right-click a word.",
    "вдруг\nвнезапно\nоднако\nвздохнул\nпочувствовал, как":
        "suddenly\nall of a sudden\nhowever\nsighed\nfelt that",
    "По главам: больше всего штампов сверху":
        "By chapter: the most clichés on top",
    "Найти все места":
        "Find all places",
    "Список мест по всем главам: клик - открыть, правый клик - убрать или заменить":
        "Places in all chapters: click - open, right-click - remove or replace",
    "Выбрать места…":
        "Choose places…",
    "Заменить везде:":
        "Replace everywhere:",
    "Найдено: {n}. Сними галочки там, где «{entry}» нужно оставить. Перед заменой каждая глава кладётся в «Версии файла» - всё можно вернуть.":
        "Found: {n}. Untick the places where «{entry}» should stay. Before replacing, each chapter is saved to «File versions» - everything can be undone.",
    "пусто - просто убрать слово":
        "empty - just remove the word",
    "«{phrase}» в моих штампах: по главам {found} {n}":
        "«{phrase}» in my clichés: {found} {n} across chapters",
    "«{phrase}» уже в моих штампах":
        "«{phrase}» is already in my clichés",
    "Список пуст: «Ещё → Мои штампы» или правый клик по слову в тексте":
        "The list is empty: «More → My clichés» or right-click a word in the text",
    "Убрать «{found}» здесь":
        "Remove «{found}» here",
    "Заменить здесь на…":
        "Replace here with…",
    "Заменить «{entry}» везде…":
        "Replace «{entry}» everywhere…",
    "Заменить":
        "Replace",
    "Чем заменить «{found}»? Пусто - просто убрать.":
        "Replace «{found}» with what? Empty - just remove it.",
    "Мои штампы":
        "My clichés",
    "Текст в этом месте уже изменился. Обновляю список.":
        "The text here has already changed. Refreshing the list.",
    "«{entry}» в главах не встречается.":
        "«{entry}» does not occur in the chapters.",
    "«{n}» не изменена:\n{error}":
        "«{n}» was not changed:\n{error}",
    # text/deadline.py
    "Убрать дедлайн":
        "Remove deadline",
    "Книга (категория):":
        "Book (category):",
    "Сколько слов:":
        "How many words:",
    "К какому числу:":
        "By what date:",
    "Сначала создай категорию для книги":
        "Create a category for the book first",
    # text/editor.py
    "Вернуть":
        "Restore",
    "Отменить":
        "Undo",
    "Выделить всё":
        "Select all",
    "Добавить «{word}» в словарь":
        "Add «{word}» to the dictionary",
    "Считать «{word}» персонажем":
        "Treat «{word}» as a character",
    "Заметка на полях   Ctrl+M":
        "Margin note   Ctrl+M",
    "В мои штампы: «{phrase}»":
        "Add to my clichés: «{phrase}»",
    "Вырезать":
        "Cut",
    "Копировать":
        "Copy",
    "Вставить":
        "Paste",
    "Нет вариантов":
        "No suggestions",
    "Поменять местами: этот файл - в основное окно, чтобы править":
        "Swap: put this file in the main window to edit it",
    "Закрыть панель   F4":
        "Close panel   F4",
    "Версия постарше":
        "Older version",
    "Версия поновее":
        "Newer version",
    "Перенести панель на другую сторону от текста":
        "Move the panel to the other side of the text",
    "{stem} · версия от {n}":
        "{stem} · version from {n}",
    "{n} из {n2}   ·   {summary}":
        "{n} of {n2}   ·   {summary}",
    # text/replace.py
    "Снять все":
        "Untick all",
    "Отметить все":
        "Tick all",
    "Заменить отмеченные":
        "Replace ticked",
    "Заменить на:":
        "Replace with:",
    "Заменено {done} в {files} {n}. Нажми сюда - отменить":
        "Replaced {done} in {files} {n}. Click here to undo",
    "пусто - просто убрать":
        "empty - just remove",
    "С учётом регистра":
        "Match case",
    "Целое слово":
        "Whole word",
    "Все падежи (для имён и названий)":
        "All cases (for names and titles)",
    "«Кира → Мира» заменит и «Киры» на «Миры», и «Кирой» на «Мирой»":
        "«Кира → Мира» also replaces «Киры» with «Миры» and «Кирой» with «Мирой»",
    "Найти:":
        "Find:",
    "Напиши, что искать":
        "Type what to find",
    "{n} {n2} в {n3} {n4}. Сними галочки там, где менять не надо. Перед заменой каждый файл кладётся в «Версии файла».":
        "{n} {n2} in {n3} {n4}. Untick the places that should not change. Before replacing, each file is saved to «File versions».",
    "Нечего отменять: замен во всех главах ещё не было":
        "Nothing to undo: there have been no replacements across all chapters yet",
    "Замена":
        "Replace",
    "«{stem}» не изменён:\n{error}":
        "«{stem}» was not changed:\n{error}",
    # text/rhythm.py
    "Каждый столбик - предложение по порядку. Жёлтые - короткие (до {SHORT} слов), красные - длинные (от {LONG}), линия - средняя длина. Наведи - видно предложение, клик - перейти к нему.":
        "Each bar is a sentence, in order. Yellow - short (up to {SHORT} words), red - long (from {LONG}), the line - average length. Hover to see the sentence, click to jump to it.",
    "Ритм считается для главы, а не для таблицы или доски":
        "Rhythm is counted for a chapter, not for a table or a board",
    # text/speakers.py
    "Кто говорит - по «сказала Кира», по «сказал он» (кто упоминался последним), по действию в абзаце перед репликой и по очерёдности в разговоре двоих. Выбери персонажа - ниже будет видно, сколько он говорит в каждой главе.":
        "Who speaks - by «сказала Кира», by «сказал он» (whoever was mentioned last), by the action in the paragraph before the line and by turn-taking in a two-person talk. Choose a character to see below how much they speak in each chapter.",
    "Всего {replies} {n}":
        "Total {replies} {n}",
    ", у {unknown} не понять, кто говорит - их можно найти через «Кто говорит: проверить реплики»":
        ", for {unknown} it is unclear who speaks - find them via «Who speaks: check lines»",
    "Из них {guessed} - угадано по очерёдности в разговоре":
        "Of these, {guessed} were guessed by turn-taking in the conversation",
    "Сначала добавь персонажей: «Персонажи» слева или правый клик по имени":
        "Add characters first: «Characters» on the left or right-click a name",
    "Пока нет глав":
        "No chapters yet",
    # text/speech.py
    "Читаю вслух - можно править дальше. F5 - остановить":
        "Reading aloud - you can keep editing. F5 - stop",
    "Вслух читается глава, а не таблица, доска или хронология":
        "Reading aloud works for a chapter, not a table, a board or a timeline",
    "Чтение вслух":
        "Read aloud",
    "Дальше курсора читать нечего: поставь курсор выше":
        "Nothing to read after the cursor: put the cursor higher",
    "Голос перестал читать: ":
        "The voice stopped reading: ",
    # ui/colors.py
    "Кнопка":
        "Button",
    "Важное":
        "Important",
    "Включено":
        "On",
    "Щёлкни - кубик бросится":
        "Click - the die is rolled",
    "Контраст текста {n}:1 - {n2}.\nРеплики {n3}:1. Для долгого чтения удобно примерно 7–12.":
        "Text contrast {n}:1 - {n2}.\nDialogue {n3}:1. For long reading about 7–12 is comfortable.",
    "Выбрать цвет в палитре":
        "Pick a color from the palette",
    "Темнее - светлее":
        "Darker - lighter",
    "Как свою…":
        "Save as mine…",
    "Сохранить эти цвета как свою тему с именем":
        "Save these colors as your own theme with a name",
    "Сбросить":
        "Reset",
    "Вернуть цвета выбранной темы, убрать мои правки":
        "Bring back the colors of the selected theme, drop my edits",
    "Сдвигает все цвета обеих тем разом":
        "Shifts all colors of both themes at once",
    "Днём включать дневную тему":
        "Switch to the day theme in the daytime",
    "Перед сменой дневная тема плавно темнеет, а потом за пару секунд перетекает в ночную. Утром наоборот. Прочитать текст можно в любой момент перехода.":
        "Before switching, the day theme smoothly darkens, then flows into the night theme within a couple of seconds. In the morning it is the other way round. The text stays readable at any moment of the transition.",
    "Как будет выглядеть":
        "Preview",
    "Настраиваю:":
        "Editing:",
    "Холоднее":
        "Cooler",
    "Теплее":
        "Warmer",
    "переход":
        "transition",
    "Своя тема":
        "My theme",
    "Как назвать тему?":
        "What to call the theme?",
    "Так называется встроенная тема, выбери другое имя.":
        "A built-in theme has this name, choose another one.",
    # ui/dialogs.py
    "Мысль, вопрос к себе, что проверить… В книгу не попадает.":
        "A thought, a question to yourself, something to check… It does not go into the book.",
    "К абзацу: {quote}":
        "To the paragraph: {quote}",
    "Щёлкни по клавишам и нажми новое сочетание. Пустое - без клавиши.":
        "Click the keys and press a new combination. Empty - no key.",
    "Подвести мышь к левому краю окна - файлы, к правому - знаки, таймер и кубики.":
        "Move the mouse to the left edge of the window - files; to the right - marks, timer and dice.",
    "Вернуть как было":
        "Restore defaults",
    "Ещё раз":
        "Again",
    "Забыл пароль? Войти по коду":
        "Forgot the password? Sign in with a code",
    "Неверный пароль. Следующая попытка через {left} с":
        "Wrong password. Next attempt in {left} s",
    "Неверный пароль":
        "Wrong password",
    "Введи пароль":
        "Enter the password",
    "Нужно хотя бы 6 символов":
        "At least 6 characters",
    "Пароли не совпадают":
        "The passwords do not match",
    "Файл ключа повреждён ({name}). Возьми его из резервной копии.":
        "The key file is damaged ({name}). Take it from a backup.",
    "Если забудешь пароль, этим кодом можно будет войти и поставить новый. Запиши его на бумагу или в менеджер паролей - больше он нигде не покажется. Не храни его в папке StungKir: кто найдёт код, тот откроет тексты.":
        "If you forget the password, this code lets you sign in and set a new one. Write it on paper or in a password manager - it will not be shown anywhere again. Do not keep it in the StungKir folder: whoever finds the code can open the texts.",
    "Я записал код":
        "I wrote the code down",
    "Скопировать":
        "Copy",
    "Введи код восстановления, который блокнот показал, когда ставили пароль. Дефисы и регистр не важны.":
        "Enter the recovery code the notepad showed when the password was set. Dashes and case do not matter.",
    "Войти":
        "Sign in",
    "Код не подходит. Проверь, нет ли опечатки.":
        "The code does not fit. Check for typos.",
    # ui/files.py
    "Переименовать":
        "Rename",
    "Глава обновилась с другого устройства":
        "The chapter was updated from another device",
    "Глава изменилась":
        "The chapter changed",
    "«{stem}» изменили на другом устройстве.\nТвои несохранённые правки останутся в версиях.":
        "«{stem}» was changed on another device.\nYour unsaved edits will stay in the versions.",
    "{n} обновилась с другого устройства":
        "{n} was updated from another device",
    "«{stem}» удалили или переименовали снаружи. Текст остался здесь - сохранишь, и глава появится снова":
        "«{stem}» was deleted or renamed outside. The text stayed here - save it, and the chapter will appear again",
    "Не записалось: {n}. Сохрани вручную":
        "Not written: {n}. Save manually",
    "«{name}» - у категории есть обложка. Правый клик → «Обложка…»":
        "«{name}» - the category has a cover. Right-click → «Cover…»",
    "Создано в «{name}»: {n}":
        "Created in «{name}»: {n}",
    "Не текст - блокнот его не открывает. ":
        "Not text - the notepad does not open it. ",
    "Копия от программы синхронизации: глава поменялась на двух устройствах. Открой - покажу разницу и дам выбрать":
        "A copy from the sync program: the chapter changed on two devices. Open it - I will show the difference and let you choose",
    "Категория":
        "Category",
    "Куда положить:":
        "Where to put it:",
    "Новая категория":
        "New category",
    "Такая категория уже есть: «{name}».":
        "A category with this name already exists: «{name}».",
    "Категория не создана. {n}":
        "The category was not created. {n}",
    "Новый файл":
        "New file",
    "Файл с таким названием уже есть: «{name}».":
        "A file with this name already exists: «{name}».",
    "Файл не создан. {n}":
        "The file was not created. {n}",
    "Новая таблица":
        "New table",
    "Файл с таким названием уже есть.":
        "A file with this name already exists.",
    "Не получилось создать:\n{error}":
        "Could not create it:\n{error}",
    "Новая доска":
        "New board",
    "Новая хронология":
        "New timeline",
    "Главу":
        "Chapter",
    "Таблицу":
        "Table",
    "Доску сюжета":
        "Story board",
    "Хронологию":
        "Timeline",
    "Категорию":
        "Category",
    "Книга собрана: {name}, {n}":
        "The book is built: {name}, {n}",
    "Собрать книгу":
        "Build the book",
    "Для Word нужна библиотека python-docx.\nЗапусти install.sh ещё раз, он её поставит.":
        "Word export needs the python-docx library.\nRun install.sh again, it will install it.",
    "Эти строки целиком в квадратных скобках. Скобки - это пометки для себя, при сборке они вырезаются:\n\n{shown}{more}\n\nЕсли это заголовки, их можно сделать заголовками. В тексте заголовок пишется так: «# Пролог».":
        "These lines are entirely in square brackets. Brackets are notes for yourself, they are cut out when building:\n\n{shown}{more}\n\nIf these are headings, you can make them headings. In the text a heading is written like this: «# Prologue».",
    "Книга не собрана: {error}.{kept}":
        "The book was not built: {error}.{kept}",
    "Добавлено: {added}":
        "Added: {added}",
    "Добавить файлы":
        "Add files",
    "Перемещение":
        "Moving",
    "Не получилось переместить:\n{error}":
        "Could not move it:\n{error}",
    "Файл повреждён":
        "The file is damaged",
    "«{stem}» не читается - похоже, файл испорчен (оборвалась запись или синхронизация). Он открыт пустым, а то, что в нём было, сохранено в «Версиях файла». Если ничего не менять, файл останется как есть.":
        "«{stem}» cannot be read - the file seems to be broken (a write or a sync was cut off). It is opened empty, and what was in it is saved in «File versions». If you change nothing, the file stays as it is.",
    "Кодировка":
        "Encoding",
    "Часть символов в «{stem}» не распознана, они показаны знаком �. Если сохранить, они так и останутся, но точная копия файла сохранена в {n}. Лучше сначала проверь текст.":
        "Some characters in «{stem}» were not recognized, they are shown as �. If you save, they will stay that way, but an exact copy of the file is saved in {n}. Better check the text first.",
    "Открыть":
        "Open",
    "Этот файл не расшифровывается: он зашифрован другим паролем или повреждён (например, оборвалась синхронизация). Предыдущие версии - в «Версиях файла», копии - в резервных копиях.":
        "This file cannot be decrypted: it is encrypted with another password or damaged (for example, a sync was cut off). Earlier versions are in «File versions», copies are in the backups.",
    "Не получилось открыть файл:\n{n}":
        "Could not open the file:\n{n}",
    "Файл был в кодировке {encoding}: при сохранении станет UTF-8":
        "The file was in the {encoding} encoding: it will become UTF-8 when saved",
    "Глава успела измениться на другом устройстве. Записана твоя версия, а та - в «Версиях файла»":
        "The chapter changed on another device in the meantime. Your version was written, and that one is in «File versions»",
    "Не получилось сохранить:\n{error}":
        "Could not save:\n{error}",
    "Сохранено":
        "Saved",
    "Автосохранение не удалось: {n}. Сохрани вручную":
        "Autosave failed: {n}. Save manually",
    "Несохранённый текст":
        "Unsaved text",
    "Сохранить изменения?":
        "Save changes?",
    "Весь текст скопирован":
        "All text copied",
    "В режиме «только вперёд» версии не возвращаются":
        "In «forward only» mode versions cannot be restored",
    "Сначала открой файл":
        "Open a file first",
    "Версия возвращена. Сохрани, если всё так":
        "The version is restored. Save if it is right",
    "Удалить в корзину":
        "Move to trash",
    "Новый файл здесь":
        "New file here",
    "Новая таблица здесь":
        "New table here",
    "Новая доска здесь":
        "New board here",
    "Новая хронология здесь":
        "New timeline here",
    "Больше не справочник мира":
        "No longer a world reference",
    "Сделать справочником мира":
        "Make it a world reference",
    "Обложка…":
        "Cover…",
    "Открыть рядом":
        "Open beside",
    "Версии…":
        "Versions…",
    "Цель главы…":
        "Chapter goal…",
    "Выложить на сайт…":
        "Publish to the site…",
    "Сохранить как шаблон…":
        "Save as template…",
    "Вернулось: «{n}»":
        "Restored: «{n}»",
    "История версий":
        "Version history",
    "Переименовано, но старые версии не переехали и лежат под прежним именем в папке {n}. Подробности в {ERROR_LOG}.":
        "Renamed, but the old versions did not move and are kept under the old name in the folder {n}. Details in {ERROR_LOG}.",
    "Такое название уже занято.":
        "This name is already taken.",
    "Не переименовано. {n}":
        "Not renamed. {n}",
    "Отправить {what} «{name}» в корзину?\nТам он пролежит {TRASH_DAYS} дней, и его можно вернуть.":
        "Move the {what} «{name}» to the trash?\nIt will stay there for {TRASH_DAYS} days and can be restored.",
    "«{n}» в корзине. Нажми сюда - вернуть":
        "«{n}» is in the trash. Click here to bring it back",
    "Не получилось отправить в корзину: {n}":
        "Could not move it to the trash: {n}",
    # ui/markup.py
    "Ударение ставится сразу после гласной: поставь курсор за ней":
        "The stress mark goes right after a vowel: put the cursor after it",
    # ui/panels.py
    "Убрать пример":
        "Remove sample",
    " мин":
        " min",
    "Заготовки для мира…":
        "World presets…",
    "Добавить файлы (текст, Word, книги, таблицы)…":
        "Add files (text, Word, books, tables)…",
    "Импорт из Scrivener…":
        "Import from Scrivener…",
    "Точки возврата…":
        "Restore points…",
    "Корзина…":
        "Trash…",
    "Поиск в главе":
        "Find in chapter",
    "Найти и заменить во всех главах…":
        "Find and replace in all chapters…",
    "Отменить последнюю замену во всех главах":
        "Undo the last replacement in all chapters",
    "Копировать всё":
        "Copy all",
    "Настроить цвета и дневную тему…":
        "Set up colors and the day theme…",
    "Убрать всё - только текст":
        "Hide everything - text only",
    "Вернуть всё":
        "Show everything",
    "Выбрать свою картинку…":
        "Choose my own picture…",
    "Закрыть панель рядом":
        "Close the side panel",
    "Панель рядом":
        "Side panel",
    "Во весь экран":
        "Full screen",
    "Статистика":
        "Statistics",
    "Цель этой главы":
        "This chapter's goal",
    " (сейчас {chapter})":
        " (now {chapter})",
    "Дедлайн книги…":
        "Book deadline…",
    "Кто в какой главе":
        "Who is in which chapter",
    "Ритм главы":
        "Chapter rhythm",
    "Реплики персонажей":
        "Characters' lines",
    "Кто говорит: проверить реплики":
        "Who speaks: check lines",
    "Читать вслух":
        "Read aloud",
    "Проверить написание имён":
        "Check name spelling",
    "Мои штампы…":
        "My clichés…",
    "Найти мои штампы во всех главах":
        "Find my clichés in all chapters",
    "Настройки…":
        "Settings…",
    "Горячие клавиши - посмотреть и поменять…":
        "Hotkeys - view and change…",
    "Как увидит читатель (книга, телефон, читалка)":
        "How the reader will see it (book, phone, e-reader)",
    "Антистресс":
        "Anti-stress",
    "О программе":
        "About",
    "Добавить пример-проект":
        "Add a sample project",
    "Сменить пароль…":
        "Change password…",
    "Новый код восстановления…":
        "New recovery code…",
    "Снять пароль…":
        "Remove password…",
    "Поставить пароль…":
        "Set a password…",
    "Днём: {n}":
        "Daytime: {n}",
    "Слева: файлы, меню, знаки и таймер. Подведи мышь к левому краю":
        "On the left: files, menu, marks and timer. Move the mouse to the left edge",
    "Старт":
        "Start",
    "Сохранить и выйти":
        "Save and quit",
    "Когда время выйдет, StungKir всё сохранит и закроется сам":
        "When the time is up, StungKir will save everything and close by itself",
    "Картинка вставлена: в книге и превью она будет на своём месте":
        "The picture is inserted: in the book and the preview it will be in its place",
    "Картинку можно вставить в главу - открой её":
        "A picture can be inserted into a chapter - open one",
    "Это не картинка: подойдут PNG, JPG, GIF, WebP":
        "This is not a picture: PNG, JPG, GIF, WebP will do",
    "Картинка в текст…":
        "Picture into text…",
    "Строка [картинка: файл] - в книге, «Как увидит читатель» и на сайте будет картинка":
        "The line [картинка: файл] becomes a picture in the book, in «How the reader will see it» and on the site",
    "Поиск…":
        "Search…",
    "Поиск по всем файлам":
        "Search all files",
    "Слово или фраза…":
        "A word or phrase…",
    "Заменить…":
        "Replace…",
    "Найти и заменить во всех главах":
        "Find and replace in all chapters",
    # ui/progress.py
    "Цель на день":
        "Daily goal",
    "Первое число - слов в открытой главе. «За день» - сколько написано сегодня во всех главах вместе, поэтому при переходе в другую главу не обнуляется. Вставленное из буфера в «за день» не идёт":
        "The first number is the words in the open chapter. «Today» is how much you wrote today in all chapters together, so it does not reset when you switch chapters. Text pasted from the clipboard does not count towards «today»",
    " (сегодня вставлено {n}).":
        " (pasted today: {n}).",
    "Цель на сегодня выполнена: {n}":
        "Today's goal is reached: {n}",
    "Цель главы выполнена: {n}":
        "Chapter goal reached: {n}",
    "Цель главы":
        "Chapter goal",
    "Сколько слов должно быть в «{stem}» (0 - без цели):":
        "How many words should «{stem}» have (0 - no goal):",
    "Сначала открой главу":
        "Open a chapter first",
    "Огонёк серии: {n}":
        "Streak flame: {n}",
    "Сколько слов в день (0 - без цели):":
        "Words per day (0 - no goal):",
    "Таймер на {minutes} мин: {end}":
        "Timer for {minutes} min: {end}",
    "Таймер остановлен":
        "Timer stopped",
    "Осталась минута":
        "One minute left",
    ". Всё сохранено, закрываю…":
        ". Everything is saved, closing…",
    # ui/project.py
    "Импорт":
        "Import",
    "В «{name}» {n} {n2}: {names}{more}.\n\nРазрезать на главы или положить одним файлом?":
        "«{name}» has {n} {n2}: {names}{more}.\n\nSplit into chapters or keep as one file?",
    "Импорт из Scrivener":
        "Import from Scrivener",
    "Из «{name}» будут созданы категории:\n{lines}\n\nСцены внутри папки станут одной главой через «* * *», синопсисы и заметки - заметками на полях. Сам проект Scrivener не меняется.":
        "These categories will be created from «{name}»:\n{lines}\n\nScenes inside a folder become one chapter separated by «* * *», synopses and notes become margin notes. The Scrivener project itself is not changed.",
    "В проекте не нашлось текстов.":
        "No texts were found in the project.",
    "Не получилось: {error}.":
        "It did not work: {error}.",
    "Точка возврата":
        "Restore point",
    "Как назвать точку? Например: «перед правкой второй части».":
        "What to call the point? For example: «before editing part two».",
    "Точка возврата поставлена":
        "Restore point set",
    "Не получилось сохранить главу, точка не поставлена.":
        "Could not save the chapter, the point was not set.",
    "Точка не поставлена: {error}":
        "The point was not set: {error}",
    "Книга возвращена к точке":
        "The book is back at the restore point",
    "Вернуть всю книгу к точке «{n}» ({when})?\n\nНынешнее состояние сначала сохранится отдельной точкой, так что это можно отменить. История версий глав и статистика останутся как есть.":
        "Return the whole book to the point «{n}» ({when})?\n\nThe current state is saved as a separate point first, so this can be undone. Chapter version history and statistics stay as they are.",
    "Вернуть книгу":
        "Return the book",
    "Не получилось сохранить текущую главу, ничего не менял.":
        "Could not save the current chapter, nothing was changed.",
    "Книга не возвращена, всё осталось как было: {error}":
        "The book was not returned, everything stayed as it was: {error}",
    "Удалить точку возврата":
        "Delete restore point",
    "Удалить точку «{n}»? Её не вернуть.":
        "Delete the point «{n}»? It cannot be restored.",
    # ui/search.py
    "Ничего не нашлось":
        "Nothing found",
    "{current} из {total}":
        "{current} of {total}",
    "нет":
        "none",
    "Напиши хотя бы две буквы":
        "Type at least two letters",
    "{total} {what} в {files_hit} {n}{extra}":
        "{total} {what} in {files_hit} {n}{extra}",
    "Пометок нет. Поставь [вот так] в тексте или нажми F7":
        "No marks. Put [like this] in the text or press F7",
    "Ни одного штампа из списка - чисто":
        "None of the clichés from the list - clean",
    "Везде понятно, кто говорит":
        "It is clear everywhere who speaks",
    # ui/security.py
    "Пароль":
        "Password",
    "Код восстановления":
        "Recovery code",
    "Код восстановления появился в новой версии StungKir, а пароль ставили раньше - для этих текстов кода ещё нет. Войди паролем: блокнот сразу предложит создать код.":
        "The recovery code appeared in a newer version of StungKir, and the password was set earlier - these texts have no code yet. Sign in with the password: the notepad will offer to create a code right away.",
    "Новый пароль":
        "New password",
    "Не получилось записать файл ключа, пароль прежний:\n{error}":
        "Could not write the key file, the password is unchanged:\n{error}",
    "Не получилось записать файл ключа:\n{error}":
        "Could not write the key file:\n{error}",
    "Дошифровал файлов: {done}":
        "Files encrypted after a pause: {done}",
    "Поставить пароль":
        "Set a password",
    "Все тексты будут храниться зашифрованными.\n\n• Ты получишь код восстановления. Если потеряешь и пароль, и код, вернуть тексты не получится никак.\n• На телефоне через Syncthing файлы будут нечитаемы, пока не появится своя версия StungKir для телефона.\n• Названия глав и категорий остаются видны.\n\nПродолжить?":
        "All texts will be stored encrypted.\n\n• You will get a recovery code. If you lose both the password and the code, the texts cannot be recovered at all.\n• On a phone synced via Syncthing the files will be unreadable until StungKir for the phone learns passwords.\n• Chapter and category names stay visible.\n\nContinue?",
    "Пароль поставлен":
        "Password set",
    "Для шифрования нужна библиотека cryptography.\nЗапусти install.sh ещё раз, он её поставит.":
        "Encryption needs the cryptography library.\nRun install.sh again, it will install it.",
    "Пароль не поставлен":
        "Password not set",
    "Пароль сменён":
        "Password changed",
    "Не получилось записать файл ключа, пароль остался прежним:\n{error}":
        "Could not write the key file, the password stayed the same:\n{error}",
    "Новый код восстановления сохранён, старый больше не работает":
        "New recovery code saved, the old one no longer works",
    "Пароль снят":
        "Password removed",
    "Файлы расшифрованы, но файл ключа не удалился:\n{error}":
        "The files are decrypted, but the key file was not deleted:\n{error}",
    # ui/widgets.py
    "Пока идёт таймер, ласка бежит":
        "While the timer runs, the weasel runs",
    # ui/window.py
    "Латиница выключена: переключи раскладку на русскую":
        "Latin letters are off: switch the keyboard layout to Russian",
    "Режим «только вперёд»: стирать нельзя, пиши дальше":
        "«Forward only» mode: no erasing, keep writing",
    "Проверка орфографии выключена: нет русского словаря":
        "Spell checking is off: no Russian dictionary",
    "Без отвлечений. F10 - вернуть всё":
        "No distractions. F10 - bring everything back",
    "Картинка под текстом":
        "Picture under the text",
    "Картинка маленькая: {n}×{n2}, а окно на твоём экране - {n3}×{n4} точек. Её придётся растянуть, и она будет мыльной.\n\nДля чёткой картинки нужна от {n3}×{n4} и больше. Блокнот хранит её без пережатия и рисует в настоящих точках экрана - качество теряется только при растягивании.":
        "The picture is small: {n}×{n2}, and the window on your screen is {n3}×{n4} pixels. It would have to be stretched and would look blurry.\n\nFor a sharp picture you need {n3}×{n4} or more. The notepad keeps it without recompression and draws it in real screen pixels - quality is lost only when stretching.",
    "Картинка под текстом. Насколько её притемнить - «Фон под текстом → Затемнение»":
        "Picture under the text. How much to darken it - «Background under the text → Dimming»",
    "Не получилось сохранить картинку: {error}":
        "Could not save the picture: {error}",
    "Всё вернулось на экран":
        "Everything is back on the screen",
    "На экране только текст. Вернуть: Вид → На экране → Вернуть всё":
        "Only text on the screen. To bring it back: View → On screen → Show everything",
    "Такой главы больше нет":
        "This chapter no longer exists",
    "Только вперёд: стирать нельзя":
        "Forward only: no erasing",
    "Стирать снова можно":
        "Erasing is allowed again",
    "Предпросмотр - для главы, а не таблицы, доски или хронологии":
        "Preview is for a chapter, not a table, a board or a timeline",
    "Горячие клавиши сохранены":
        "Hotkeys saved",
    "Горячие клавиши - как были":
        "Hotkeys - unchanged",
    "Недельная копия книги сделана":
        "Weekly copy of the book made",
    "Напомню отдохнуть глазам через {minutes} минут за текстом":
        "I will remind you to rest your eyes after {minutes} minutes of writing",
    "Напоминание о перерыве выключено":
        "Break reminder is off",
    "Звук машинки выключен":
        "Typewriter sound is off",
    "Звук машинки: {n}":
        "Typewriter sound: {n}",
    "Настройки применены":
        "Settings applied",
    # ui/windows.py
    "до":
        "to",
    "Сохранить":
        "Save",
    "с":
        "from",
    "Вернуться к точке":
        "Go back to the point",
    "Эту картинку не получилось открыть. Подойдут JPG, PNG, WebP, BMP.":
        "This picture could not be opened. JPG, PNG, WebP, BMP will do.",
    "За {STATS_DAYS} дней: {n}   ·   в среднем {n2} в день письма   ·   лучший день: {best} ({best_day:%d.%m})":
        "In {STATS_DAYS} days: {n}   ·   on average {n2} per writing day   ·   best day: {best} ({best_day:%d.%m})",
    "День засчитан от {STREAK_WORDS} слов. Писал на телефоне или от руки - кликни по дню, появится галочка.":
        "A day counts from {STREAK_WORDS} words. Wrote on the phone or by hand - click the day, a tick appears.",
    "За год: {n}   ·   дней с текстом: {active_days}":
        "This year: {n}   ·   days with text: {active_days}",
    "   ·   лучший месяц: {best_month} ({best_month_words})":
        "   ·   best month: {best_month} ({best_month_words})",
    "Дней подряд: {current}   ·   рекорд: {best}":
        "Days in a row: {current}   ·   record: {best}",
    "Название книги":
        "Book title",
    "Можно оставить пустым":
        "Can be left empty",
    "Главы идут в том же порядке, что и в списке слева. Сними галочку, чтобы главу не включать.":
        "Chapters go in the same order as in the list on the left. Untick a chapter to leave it out.",
    "Размер страницы (для PDF и Word)":
        "Page size (for PDF and Word)",
    " пт":
        " pt",
    "Размер шрифта":
        "Font size",
    "Контакты для титула рукописи: почта, телефон":
        "Contacts for the manuscript title page: email, phone",
    "Глава с новой страницы":
        "Each chapter on a new page",
    "Заголовки глав":
        "Chapter headings",
    "Без пометок [ … ]":
        "Without marks [ … ]",
    "Собрать":
        "Build",
    "В плане книги отмечена «не в книгу». Поставь галочку, если всё же нужна":
        "Marked «not in the book» in the book plan. Tick it if you need it after all",
    "Цвета и темы…":
        "Colors and themes…",
    "Все цвета, свои темы, дневная тема по времени, теплота - с образцом":
        "All colors, your own themes, the day theme on a schedule, warmth - with a preview",
    "Меняется после перезапуска. Нет перевода - надпись остаётся русской":
        "Changes after a restart. Without a translation a label stays in Russian",
    "Только русские буквы в тексте":
        "Only Russian letters in the text",
    "Сохранять само (после паузы в наборе)":
        "Save by itself (after a pause in typing)",
    "Русские голоса, которые стоят в системе. На Debian получше звучат голоса RHVoice (sudo apt install rhvoice-russian): Александр, Анна, Елена, Ирина":
        "Russian voices installed in the system. On Debian the RHVoice voices sound better (sudo apt install rhvoice-russian): Aleksandr, Anna, Elena, Irina",
    "Окошки без теней (если вокруг них чёрная рамка)":
        "Windows without shadows (if there is a black frame around them)",
    " слов":
        " words",
    "без цели":
        "no goal",
    "не делать - или папка на флешке, в облаке":
        "don't - or a folder on a USB stick, in the cloud",
    "Раз в неделю вся книга архивом копируется сюда. Флешки нет - копия сделается в следующий раз, когда папка найдётся. Хранятся последние 8.":
        "Once a week the whole book is copied here as an archive. No USB stick - the copy will be made next time the folder is found. The last 8 are kept.",
    "Сбросить всё":
        "Reset everything",
    "Папка для копий":
        "Folder for copies",
    "Вернуть эту версию":
        "Restore this version",
    "Рядом с текстом":
        "Beside the text",
    "Эта версия - в панели рядом с главой: пиши и сверяйся":
        "This version is in the panel next to the chapter: write and compare",
    "Точка возврата - вся книга целиком на этот момент: главы, справочник, заметки, доски. Поставь её перед большой правкой, а если не понравится - вернись. История версий глав и статистика при возврате не меняются.":
        "A restore point is the whole book at this moment: chapters, reference, notes, boards. Set one before a big edit, and if you do not like the result, go back. Chapter version history and statistics do not change when returning.",
    "Новая точка":
        "New point",
    "Картинка книги или категории: видна значком в списке слева и становится обложкой, когда собираешь книгу в PDF или EPUB. С паролем шифруется вместе с текстами.":
        "A picture for a book or category: shown as an icon in the list on the left and becomes the cover when you build the book as PDF or EPUB. With a password it is encrypted together with the texts.",
    "Выбрать картинку…":
        "Choose a picture…",
    "Убрать обложку":
        "Remove cover",
    "Обложки пока нет":
        "No cover yet",
    "Обложка":
        "Cover",
    "Язык":
        "Language",
    "Язык поменяется после перезапуска":
        "The language will change after a restart",
    # ui/world.py
    "Версий пока нет: они появляются при сохранении":
        "No versions yet: they appear when you save",
    "Сначала сохрани главу: заметки хранятся рядом с ней":
        "Save the chapter first: notes are kept next to it",
    "У «{name}» пока нет заметки в справочнике":
        "«{name}» has no note in the reference yet",
    "Сравнивать можно главу: открой её":
        "Only a chapter can be compared: open one",
    "Рядом пока нечего открыть: нужен ещё хотя бы один файл":
        "Nothing to open beside yet: you need at least one more file",
    "Написание имён":
        "Name spelling",
    "Пока не с чем сравнивать. Добавь имена в «Персонажи» или сделай категорию справочником мира: правый клик по ней в списке слева.":
        "Nothing to compare with yet. Add names to «Characters» or make a category a world reference: right-click it in the list on the left.",
    "Всё сходится: каждое имя везде написано одинаково":
        "Everything matches: each name is spelled the same everywhere",
    "«{word}» - так и задумано":
        "«{word}» is intended",
    "Персонажи и имена":
        "Characters and names",
    "Добавить имя, например Ольга":
        "Add a name, for example Kira",
    "Добавить":
        "Add",
    "Проверить, не написано ли где-то имя иначе":
        "Check whether a name is spelled differently somewhere",
    "Новый персонаж":
        "New character",
    "Как записать имя? Лучше в начальной форме: «Кира», а не «Киры» - остальные падежи найдутся сами.":
        "How to write the name? Better in the basic form: «Кира», not «Киры» - the other cases are found automatically.",
    "Слежу за персонажем «{name}»":
        "Following the character «{name}»",
    "Имя должно быть русскими буквами":
        "The name must be in Russian letters",
    "«{name}» уже в списке":
        "«{name}» is already on the list",
    "«{name}» - это форма имени «{name2}», оно уже в списке":
        "«{name}» is a form of the name «{name2}», it is already on the list",
    "Не считать «{name}»":
        "Do not count «{name}»",
    "Считаются и падежи: «Кира», «Киры», «Кирой». Клик ищет имя по всем главам, правый клик убирает из списка.":
        "Cases are counted too: «Кира», «Киры», «Кирой». Click searches the name in all chapters, right-click removes it from the list.",
    "Пока никого. Добавь имя здесь или нажми правой кнопкой на имя в тексте → «Считать персонажем».":
        "Nobody yet. Add a name here or right-click a name in the text → «Treat as a character».",
    # world/presence.py
    "Закрыть":
        "Close",
    "Число - сколько раз упомянут в главе. Клик по клетке - открыть главу на этом месте. Справа - сколько глав подряд термин отсутствовал посреди книги.":
        "The number is how many times it is mentioned in the chapter. Click a cell to open the chapter at that place. On the right - for how many chapters in a row the term was missing in the middle of the book.",
    "{name}: {n} в «{stem}»":
        "{name}: {n} in «{stem}»",
    # world/templates.py
    "Шаблон - пустые разделы, которые останется заполнить. Свой шаблон: правый клик по готовой карточке слева → «Сохранить как шаблон».":
        "A template is empty sections left to fill in. Your own template: right-click a finished card on the left → «Save as template».",
    "Удалить свой шаблон":
        "Delete my template",
    "Шаблон":
        "Template",
    "Удалить шаблон «{name}»?":
        "Delete the template «{name}»?",
    "Сохранить как шаблон":
        "Save as template",
    "Название шаблона:":
        "Template name:",
    "Шаблон «{name}» сохранён":
        "Template «{name}» saved",
    "В карточке нет разделов вида «Название: …» - шаблону не из чего взяться":
        "The card has no sections like «Title: …» - there is nothing to make a template from",
    "Не прочиталось: {error}":
        "Could not read it: {error}",
    # world/timeline.py
    "Готово":
        "Done",
    "Цвет:":
        "Color:",
    "Изменить":
        "Edit",
    "Удалить":
        "Delete",
    "Открыть главу":
        "Open chapter",
    "Цвет":
        "Color",
    "как в твоём мире: «312 г. Второй эры, весна»":
        "as in your world: «312, Second Era, spring»",
    "По этому числу события встают по порядку. Дробное - если в одном году несколько":
        "Events are ordered by this number. Use a fraction if there are several in one year",
    "Что случилось":
        "What happened",
    "Подробности…":
        "Details…",
    "Когда:":
        "When:",
    "Год (для порядка):":
        "Year (for ordering):",
    "Удалить событие":
        "Delete event",
    "+ событие":
        "+ event",
    "события идут по году; двойной клик - изменить, по пустому месту - новое":
        "events go by year; double-click to edit, on an empty spot - a new one",
    "Новое событие":
        "New event",
    # world/worldkit.py
    "Отмена":
        "Cancel",
    "Создать":
        "Create",
    "Пустые таблицы и карточки - заполнишь своим. Таблицы можно дополнять столбцами, карточки - своими пунктами.":
        "Empty tables and cards - fill them with your own. Tables can get more columns, cards your own items.",
    "Сделать категорию справочником мира (имена подчёркиваются в тексте)":
        "Make the category a world reference (names are underlined in the text)",
    # ещё: заголовки окон, подписи настроек, пункты меню
    "Как увидит читатель · {title}":
        "How the reader will see it · {title}",
    "Выложить на сайт · {name}":
        "Publish to the site · {name}",
    "Конфликт синхронизации":
        "Sync conflict",
    "Корзина":
        "Trash",
    "Рандомайзеры":
        "Randomizers",
    "На ребро!":
        "On the edge!",
    "Осталось вариантов: {left}":
        "Options left: {left}",
    "Персонаж ({n})":
        "Character ({n})",
    "Термин мира ({n})":
        "World term ({n})",
    "Любой":
        "Any",
    "Свои вызовы":
        "My challenges",
    "Карточка сцены":
        "Scene card",
    "Колонки":
        "Columns",
    "Карточки стопками по колонкам":
        "Cards stacked in columns",
    "Пробка":
        "Corkboard",
    "Карточки лежат где угодно, их можно связать нитками":
        "Cards lie anywhere and can be linked with threads",
    "План книги":
        "Book plan",
    "+ строка":
        "+ row",
    "+ столбец":
        "+ column",
    "− строка":
        "− row",
    "− столбец":
        "− column",
    "Заменить «{entry}»":
        "Replace «{entry}»",
    "Дедлайн книги":
        "Book deadline",
    "Ритм главы · {title}":
        "Chapter rhythm · {title}",
    "Цвета и темы":
        "Colors and themes",
    "Заметка на полях":
        "Margin note",
    "Горячие клавиши":
        "Hotkeys",
    "Вход по коду":
        "Sign in with a code",
    "Название категории:":
        "Category name:",
    "Название файла в «{name}»:":
        "File name in «{name}»:",
    "Название таблицы в «{name}»:":
        "Table name in «{name}»:",
    "Название доски в «{name}»:":
        "Board name in «{name}»:",
    "Название хронологии в «{name}»:":
        "Timeline name in «{name}»:",
    "Новое название:":
        "New name:",
    "Главу, таблицу, доску или категорию":
        "A chapter, table, board or category",
    "Яркий только абзац, где пишешь":
        "Only the paragraph you are writing is bright",
    "Строка всегда по центру экрана":
        "The line is always in the middle of the screen",
    "Нельзя стирать: только писать дальше":
        "No erasing: only keep writing",
    "Настройки, статистика, цели, пароль…":
        "Settings, statistics, goals, password…",
    "Файлы и импорт":
        "Files and import",
    "Вид, тема и цвета":
        "View, theme and colors",
    "Тема: {current}":
        "Theme: {current}",
    "Выделять знаки препинания":
        "Highlight punctuation",
    "Подчёркивать имена и термины мира":
        "Underline world names and terms",
    "На экране":
        "On screen",
    "Заметки на полях":
        "Margin notes",
    "Номера строк":
        "Line numbers",
    "Полоски цели: {n}":
        "Goal bars: {n}",
    "Без отвлечений":
        "No distractions",
    "Фон под текстом: {n}":
        "Background under the text: {n}",
    "Звук печатной машинки: ":
        "Typewriter sound: ",
    "выключен":
        "off",
    "Перерыв для глаз: ":
        "Eye break: ",
    "раз в {eye} мин":
        "every {eye} min",
    "Тёплый фильтр вечером":
        "Warm filter in the evening",
    "Цели и статистика":
        "Goals and statistics",
    "Пароль и копии":
        "Password and backups",
    "Затемнение картинки: {n}":
        "Picture dimming: {n}",
    "Тире, кавычки, ударение, разметка":
        "Dashes, quotes, stress marks, formatting",
    "Кубики и монетка на столе, число, вариант из списка, персонаж или термин мира, рулетка с вызовами":
        "Dice and a coin on the table, a number, an option from a list, a character or world term, a roulette with challenges",
    "Всё, что в [скобках], по всем главам":
        "Everything in [brackets], across all chapters",
    "Сколько раз встречается каждое имя":
        "How many times each name appears",
    "Прошлые сохранения этой главы":
        "Earlier saves of this chapter",
    "Прошлая версия рядом с текстом, ушедшее подсвечено":
        "The earlier version beside the text, removed parts highlighted",
    "Статусы глав, о чём они и сколько слов":
        "Chapter statuses, what they are about and how many words",
    "В PDF, Word, EPUB или один текстовый файл":
        "To PDF, Word, EPUB or a single text file",
    "Каждые 20 минут":
        "Every 20 minutes",
    "Каждые 30 минут":
        "Every 30 minutes",
    "Каждые 45 минут":
        "Every 45 minutes",
    "Каждый час":
        "Every hour",
    "Выключен":
        "Off",
    "Авто, с {NIGHT_FROM}:00 до {NIGHT_TO}:00":
        "Auto, from {NIGHT_FROM}:00 to {NIGHT_TO}:00",
    "Всегда":
        "Always",
    "Стоп":
        "Stop",
    "Не всё зашифровано":
        "Not everything is encrypted",
    "Пароль поставлен, но не везде":
        "The password is set, but not everywhere",
    "Пароль не снят":
        "The password was not removed",
    "Режим фокуса включён":
        "Focus mode on",
    "Режим фокуса выключен":
        "Focus mode off",
    "Печатная машинка: строка, где пишешь, всегда посередине экрана":
        "Typewriter: the line you are writing is always in the middle of the screen",
    "Печатная машинка выключена":
        "Typewriter off",
    "Режим фокуса":
        "Focus mode",
    "Печатная машинка":
        "Typewriter",
    "Только вперёд":
        "Forward only",
    "Статистика · {APP_NAME}":
        "Statistics · {APP_NAME}",
    "Настройки":
        "Settings",
    "Оформление":
        "Appearance",
    "Цвета":
        "Colors",
    "Текст":
        "Text",
    "Шрифт":
        "Font",
    "Размер":
        "Size",
    "Насыщенность":
        "Weight",
    "Ширина колонки":
        "Column width",
    "Межстрочный интервал":
        "Line spacing",
    "Чтение вслух (F5)":
        "Read aloud (F5)",
    "Голос":
        "Voice",
    "Звук кубиков и монетки":
        "Dice and coin sound",
    "Разное":
        "Other",
    "Тёплый фильтр (авто)":
        "Warm filter (auto)",
    "Резервные копии":
        "Backups",
    "Копия раз в неделю":
        "Weekly copy",
    "Версии · {stem}":
        "Versions · {stem}",
    "Точки возврата":
        "Restore points",
    "Обложка · {name}":
        "Cover · {name}",
    "Шаблон карточки":
        "Card template",
    "Событие":
        "Event",
    "Заготовки для мира · {category_name}":
        "World presets · {category_name}",
    # строка внизу и разделы панели
    "Категории":
        "Categories",
    "Таймер":
        "Timer",
    "таймер {minutes}:{seconds:02}":
        "timer {minutes}:{seconds:02}",
    " из {n} {words}":
        " of {n} {words}",
    " из {goal}":
        " of {goal}",
    "за день":
        "today",
    ", сокращено на {n}":
        ", cut by {n}",
    " {days} подряд":
        " {days} in a row",
    "сессия {h}:{m:02}:{s:02}":
        "session {h}:{m:02}:{s:02}",
    # кнопки левой панели
    "Создать  ▸":
        "Create  ▸",
    "Ещё  ▸":
        "More  ▸",
    "Знаки  ▸":
        "Marks  ▸",
    "Рандомайзеры…":
        "Randomizers…",
    "Пометки":
        "Marks",
    "Персонажи":
        "Characters",
    "Версии файла":
        "File versions",
    "Сравнить с версией":
        "Compare with a version",
    # значения в «Настройках» (хранятся по-русски, показываются переводом)
    "Обычный":
        "Regular",
    "Средний":
        "Medium",
    "Полужирный":
        "Semibold",
    "Жирный":
        "Bold",
    "Медленно":
        "Slow",
    "Обычно":
        "Normal",
    "Быстрее":
        "Faster",
    "Быстро":
        "Fast",
    "Как в системе":
        "System default",
    "Без звука":
        "Silent",
    "Тихо":
        "Quiet",
    "Громко":
        "Loud",
    # горячие клавиши, календарь, заголовки таблиц
    "сохранить":
        "save",
    "новая глава":
        "new chapter",
    "поиск в главе":
        "find in chapter",
    "поиск по всем файлам":
        "search all files",
    "найти и заменить во всех главах":
        "find and replace in all chapters",
    "копировать всё":
        "copy all",
    "курсив":
        "italic",
    "жирный":
        "bold",
    "тире «—»":
        "dash «—»",
    "многоточие":
        "ellipsis",
    "кавычки «»":
        "quotes «»",
    "только вперёд":
        "forward only",
    "пометка [ ]":
        "mark [ ]",
    "режим фокуса":
        "focus mode",
    "печатная машинка":
        "typewriter",
    "без отвлечений: только текст":
        "no distractions: text only",
    "во весь экран":
        "full screen",
    "шрифт крупнее":
        "larger font",
    "шрифт мельче":
        "smaller font",
    "настройки":
        "settings",
    "заметка на полях к абзацу (или двойной клик по полю)":
        "margin note for a paragraph (or double-click the margin)",
    "номера строк слева от текста":
        "line numbers to the left of the text",
    "план книги: статусы глав, о чём они и сколько слов":
        "book plan: chapter statuses, what they are about and how many words",
    "панель рядом: глава или справочник для чтения":
        "side panel: a chapter or reference to read",
    "читать главу вслух с места курсора - можно править, пока читает":
        "read the chapter aloud from the cursor - you can edit while it reads",
    "антистресс: пупырка, мячик, спиннер, песок, тумблеры":
        "anti-stress: bubble wrap, ball, spinner, sand, switches",
    "сравнить с прошлой версией - рядом с текстом":
        "compare with an earlier version - beside the text",
    "как увидит читатель: книга A5, телефон, читалка":
        "how the reader will see it: A5 book, phone, e-reader",
    "горячие клавиши":
        "hotkeys",
    "заголовок внутри главы: «# Пролог»":
        "a heading inside a chapter: «# Prologue»",
    "размер шрифта":
        "font size",
    "открыть заметку из справочника мира":
        "open a note from the world reference",
    "пн":
        "Mo",
    "вт":
        "Tu",
    "ср":
        "We",
    "чт":
        "Th",
    "пт":
        "Fr",
    "сб":
        "Sa",
    "вс":
        "Su",
    "больше":
        "more",
    "меньше":
        "less",
    "Январь":
        "January",
    "Февраль":
        "February",
    "Март":
        "March",
    "Апрель":
        "April",
    "Май":
        "May",
    "Июнь":
        "June",
    "Июль":
        "July",
    "Август":
        "August",
    "Сентябрь":
        "September",
    "Октябрь":
        "October",
    "Ноябрь":
        "November",
    "Декабрь":
        "December",
    "января":
        "January",
    "февраля":
        "February",
    "марта":
        "March",
    "апреля":
        "April",
    "мая":
        "May",
    "июня":
        "June",
    "июля":
        "July",
    "августа":
        "August",
    "сентября":
        "September",
    "октября":
        "October",
    "ноября":
        "November",
    "декабря":
        "December",
    "Персонаж":
        "Character",
    "Реплик":
        "Lines",
    "Слов":
        "Words",
    "Доля реплик":
        "Share of lines",
    "Глава":
        "Chapter",
    "Штампов":
        "Clichés",
    "На 1000 слов":
        "Per 1000 words",
    "Статус":
        "Status",
    "Год":
        "Year",
    "О чём":
        "About",
    "Всего":
        "Total",
    "Пропал":
        "Missing",
    # конфликты синхронизации
    "Оставлена твоя версия, копия в корзине":
        "Your version is kept, the copy is in the trash",
    "Взята версия из копии, твоя - в «Версиях файла»":
        "The copy's version is taken, yours is in «File versions»",
    "Обе версии оставлены":
        "Both versions are kept",
    "Копии-конфликта уже нет: синхронизация разобралась сама":
        "The conflict copy is gone: the sync sorted it out by itself",
    " (и ещё {n})":
        " (and {n} more)",
}
