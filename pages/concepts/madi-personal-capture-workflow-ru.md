---
type: concept
id: GUIDE-MADI-WORKFLOW-RU
title: "Личный workflow Мади — от телефона/Telegram до Obsidian (RU)"
tags: [guide, workflow, ru, obsidian, telegram, voice-memos, capture, ingest, mobile]
date: 2026-04-07
related: [AUDIT-023, vault-model-decision, obsidian-plugins-install-guide-ru, GUIDE-OBSIDIAN-PLUGINS-RU]
language: ru
audience: madi
last_updated: 2026-04-07
source_count: 1
status: reviewed
---
# Личный workflow Мади: от телефона до Obsidian → Claude

> Это полный setup для твоего ежедневного использования. Базируется на реальных workflow которые делают другие (Drew Bredvick + iOS Voice Memos + Claude, Hints Plugin + Telegram, Obsidian Vox).
>
> Цель: ты записал/скопировал/сказал что-то на телефоне → через 1-2 минуты это уже в Obsidian wiki, классифицировано, с тегами, кросс-ссылками. Без ручного труда. Claude Code обрабатывает на лету.

---

## Твои источники контента (как ты сам сказал)

1. **Telegram сообщения** — копируешь и вставляешь
2. **Записи встреч** — voice memos на iPhone
3. **Статьи в браузере** — Web Clipper
4. **Личные мысли** — пишешь сам в Obsidian

Каждому источнику — отдельный канал захвата. Все четыре заканчиваются в `raw/pending/` твоего нужного vault'а (Nous или Brain) → наш `ingest_pending.py` обрабатывает и кладёт правильно.

---

## ЧАСТЬ 1: Obsidian plugins — что именно установить

### 4 plugins в каждом vault (Nous + Brain) — обязательно:

| # | Plugin | Author | Зачем |
|---|--------|--------|-------|
| 1 | **Dataview** | blacksmithgu | Динамические запросы по wiki ("показать все нерешённые блокеры") |
| 2 | **Templater** | SilentVoid13 | Шаблоны новых страниц с автозаполнением frontmatter |
| 3 | **Marp Slides** | (любой автор Marp) | Slides из markdown за 30 секунд |
| 4 | **Daily Notes** (core, не community) | Obsidian | Уже встроен — включить в Settings → Core plugins |

### 6 дополнительных plugins для твоего workflow:

| # | Plugin | Author | Зачем (специально для Мади) |
|---|--------|--------|------------------------------|
| 5 | **Periodic Notes** | liamcain | Daily/weekly/monthly notes автоматом — твой ежедневный hub |
| 6 | **Tasks** | obsidian-tasks-group | `- [ ]` чекбоксы становятся настоящим трекером с фильтрами |
| 7 | **Calendar** | liamcain | Календарь сбоку → клик на дату → daily note |
| 8 | **QuickAdd** | Christian B. Madsen | Кнопка "Add new task / source / contact / lesson" с pre-filled template |
| 9 | **Advanced URI** | Vinzent | Открывать конкретные заметки из Telegram/iOS Shortcuts по URI |
| 10 | **Omnisearch** | Scambier | Полнотекстовый поиск который понимает русский / казахский лучше дефолтного |

### Установка в каждом vault:
1. Открой Obsidian
2. Settings (⚙️ внизу слева) → Community plugins → "Turn on community plugins"
3. Нажми "Browse"
4. Для каждого плагина: ищи имя → Install → Enable
5. Повтори всё для второго vault'а через vault switcher

**Время:** ~20-30 минут на оба vault'а (10 плагинов × 2 vault'а × ~1 минуту).

---

## ЧАСТЬ 2: Chrome / Safari extensions

### 1. Obsidian Web Clipper (КРИТИЧНО)
- Chrome: https://chromewebstore.google.com/detail/obsidian-web-clipper/cnjifjpddelmedmihgijeibhnjfabmlf
- Safari: App Store → "Obsidian Web Clipper"

**Конфигурация (одноразово):**
- Открой Web Clipper → Settings → Templates → Add new template
- **Template 1: "Nous source"**
  - Vault: `Nous`
  - Folder: `raw/pending`
  - Title: `{{title}}`
  - Tags: `web,article`
- **Template 2: "Brain source"**
  - Vault: `Brain`
  - Folder: `raw/pending`
  - Title: `{{title}}`
  - Tags: `web,personal`

**Использование:**
- Читаешь статью → нажимаешь иконку Web Clipper → выбираешь template → Save
- Через ~60 секунд: статья в `raw/pending/`
- Через ещё ~60 секунд: `ingest_pending.py` создаёт source page
- Через ещё ~60 секунд: всё синкается обратно на твой Mac

### 2. Telegram Web (для копи-паста с десктопа)
Не extension, а просто https://web.telegram.org или telegram desktop app. Когда ты копируешь сообщение из Telegram чата на десктопе и вставляешь в Obsidian — оно уже есть. Ничего настраивать не надо.

### 3. Save to Obsidian (бонус, опционально)
Для других сайтов где Web Clipper не работает идеально (PDF, YouTube). Альтернатива.

---

## ЧАСТЬ 3: iPhone setup (КРИТИЧНО — ежедневный capture)

### Опция A: iOS Shortcuts + iCloud (рекомендую)

**Что делает:** на iPhone ты записываешь Voice Memo → файл автоматически попадает в нужный vault через iCloud Drive → Mac обрабатывает.

**Установка:**

1. **iCloud Drive должен быть включён на iPhone и Mac** (Settings → Apple ID → iCloud → iCloud Drive ON на обоих устройствах)

2. **Создать папку в iCloud Drive** (на Mac):
   ```
   iCloud Drive/Capture/Nous/
   iCloud Drive/Capture/Brain/
   ```

3. **На Mac: создать Folder Action** через Automator (или Shortcuts):
   - Открой Automator.app
   - File → New → "Folder Action"
   - Folder receives files added to: `~/Library/Mobile Documents/com~apple~CloudDocs/Capture/Nous`
   - Drag in: "Run Shell Script"
   - Script:
     ```bash
     for f in "$@"; do
       cp "$f" "/Users/madia/Documents/Projects/Nous AGaaS/Nous/raw/pending/"
       rm "$f"
     done
     ```
   - Save as "Capture to Nous"
   - Повторить для Brain: target dir `~/Documents/Brain/raw/pending/`

4. **На iPhone: создать Shortcut**
   - Открой приложение Shortcuts
   - + (New Shortcut)
   - Add Action → "Record Audio" (Show Recording Controls = Off, Audio Quality = Normal, Start Immediately = On)
   - Add Action → "Save File" → Service: iCloud Drive → Folder: `Capture/Nous`
   - Назови shortcut: "Capture Nous"
   - Settings (...) → Add to Home Screen → Get an icon
   - Повтори для Brain: "Capture Brain" → folder Capture/Brain

**Использование на телефоне:**
- Тапнул на иконку "Capture Nous" на главном экране
- Запись начинается автоматически
- Говоришь что хочешь сохранить (1 секунда — 30 минут)
- Нажимаешь Stop
- Через ~30 секунд файл в iCloud → синкается на Mac → Folder Action кладёт в `raw/pending/Nous/`
- Через 60 секунд `ingest_pending.py` (cron) подхватывает
- Готово

**Стоимость:** $0. iCloud + Shortcuts + Automator всё бесплатно. Транскрипция в `ingest_pending.py` через Sonnet — ~$0.01 за минуту аудио (обновлю скрипт чтобы он понимал .m4a).

### Опция B: Telegram → Obsidian через bot polling (когда я добавлю polling)

**Что делает:** ты пересылаешь любое сообщение / голосовое / файл нашему Telegram боту (`@nousAGaaSbot`) → бот сохраняет его в `raw/pending/` правильного vault'а → `ingest_pending.py` обрабатывает.

**Статус:** требует ~1 час моей работы для построения `tools/telegram_poll.py`. AUDIT-023 P1 backlog item. Когда построю — ты просто пересылаешь любой контент боту с командой `/nous` или `/brain` в подписи, и оно попадает в нужный vault.

**Преимущество над Опцией A:** работает с любого устройства (не только iPhone), любой формат (текст, аудио, видео, PDF, фото), и copy-paste из других чатов идёт через "Forward to bot" в один тап.

---

## ЧАСТЬ 4: Запись встреч — workflow

Вариант A: Voice Memo на iPhone (для коротких — до 30 минут)
- Тапни Capture Nous (iOS Shortcut)
- Запиши встречу
- После встречи — файл уже в `raw/pending/`
- `ingest_pending.py` транскрибирует через Sonnet (~$0.01-0.05) и создаёт source page

Вариант B: Профессиональная запись (длинные встречи >30 мин, важные)
- Используй приложение "Just Press Record" ($5, на iPhone) — записывает в фоне, синкается в iCloud
- Или используй сторонний сервис (Otter.ai, Fireflies.ai) который автоматически даёт транскрипт
- Транскрипт копируешь и пересылаешь нашему Telegram боту → попадает в Brain или Nous

**Рекомендация:** для встреч с NetLine, Saken aga, Daniyar — Вариант A (iOS Voice Memo). Просто, бесплатно, работает.

---

## ЧАСТЬ 5: Telegram copy-paste workflow (твой текущий способ)

**Текущий workflow:**
1. Получаешь сообщение в Telegram (от Asyl, Denis, Daniyar, Saken aga)
2. Хочешь сохранить
3. Сейчас: вручную копируешь и вставляешь куда-то

**Новый workflow (после установки Telegram poll):**
1. Получаешь сообщение
2. Forward → @nousAGaaSbot
3. В подписи forward: `/nous from-asyl smartbridge` (vault + теги)
4. Бот сохраняет в `~/Documents/Projects/Nous AGaaS/Nous/raw/pending/telegram-from-asyl-2026-04-07-1830.md`
5. `ingest_pending.py` обрабатывает: создаёт source page, добавляет в правильную секцию
6. Через ~2 минуты ты видишь это в Obsidian на Mac

**Промежуточный workflow (пока telegram poll не построен):**
1. Получаешь сообщение в Telegram desktop
2. Cmd+C
3. Открываешь Obsidian → Cmd+N (новая заметка) в `raw/pending/` папке нужного vault'а
4. Cmd+V
5. Сохраняешь
6. `ingest_pending.py` через минуту обработает

---

## ЧАСТЬ 6: Connecting Opus / Sonnet — twoя точная конфигурация

**На VPS** (где живёт wiki):
- `ingest_pending.py` использует **Sonnet 4.6** (cheap, $3/$15 per M tokens)
- `wiki_lint.py` (monthly) использует **Sonnet 4.6**
- Factory CEO теперь **Sonnet 4.6** (после AUDIT-022 swap, было Opus)
- Factory Coder использует **Sonnet 4.6**
- Factory Validator использует **Gemini 2.5 Pro** (free)

**На твоём Mac в Claude Code сессиях** (что ты сейчас используешь):
- По умолчанию **Opus 4.6** для интерактивных сессий
- Можно переключить на Sonnet через `/model sonnet` командой если нужно дешевле
- qmd MCP сервер (после restart Claude Code) даёт мне поиск по wiki

**Оптимальная конфигурация:**
- **Mac (Claude Code) = Opus или Sonnet** — для творческих задач, дизайна, переговоров, написания текстов
- **VPS (cron, factory) = Sonnet** — для рутины: ingest, lint, code generation, deploy
- **VPS (validator) = Gemini Free** — для проверок которые не требуют генерации

Это уже настроено. Тебе не надо ничего менять.

---

## ЧАСТЬ 7: Настройки для phone (мобильная Obsidian app)

**Установка:**
- App Store → "Obsidian" (бесплатно, официальная)
- Открой → "Open existing vault" → выбери Brain (через iCloud Drive) ИЛИ через Obsidian Sync (платно $4/мес)

**Настройки:**
- Settings → Files & Links → "Default location for new notes" = `raw/pending`
- Settings → Editor → "Show line numbers" = ON
- Settings → Quick switcher → enable

**Использование:**
- Тапни + (новая заметка) — она автоматически создаётся в `raw/pending/`
- Пиши что хочешь, базовый markdown
- Закрываешь — файл синкается через iCloud → Mac → `ingest_pending.py` обрабатывает

**Совет:** на iPhone Obsidian медленнее чем на десктопе. Лучше использовать iOS Shortcut (Voice Memo) для быстрого capture, а Obsidian app только для просмотра и поиска.

---

## ЧАСТЬ 8: Daily routine — твоё реальное использование

### Утром (5 минут):
1. Открой Obsidian на Mac
2. Cmd+P → "Daily Note" → создаётся `daily/2026-04-07.md` с шаблоном
3. Шаблон автоматически вставляет: дата, незавершённые задачи со вчера, календарь встреч, "что важно сегодня"
4. Заполняешь 1-2 минуты

### В течение дня:
- Получил важное сообщение в Telegram → forward в наш бот (когда poll готов) ИЛИ Cmd+C, Cmd+V в Obsidian raw/pending
- Записал встречу → iOS Shortcut Capture Nous → готово
- Прочитал статью → Web Clipper → Save → готово
- Нашёл интересную идею → Voice Memo через Capture Nous → готово

### Вечером (5 минут):
1. Открой Obsidian → Daily Note
2. Просмотри что появилось в `raw/processed/` за день — Sonnet уже их обработал
3. Если нужно — попроси меня (Claude Code на Mac) синтезировать интересные insights в новые wiki pages
4. Закрой день: что сделано, что осталось на завтра

### Раз в неделю (15 минут):
1. Cmd+P → "Weekly Review"
2. Просмотри какие audits/lessons/projects обновились
3. Запусти руками `wiki_lint.py` (или подожди монday cron)
4. Если есть контрадикции — попроси меня их разрешить

---

## ЧАСТЬ 9: Примеры реальных workflow других людей (для контекста)

### Drew Bredvick — iOS Voice Memos → Obsidian → Claude
Источник: [drew.tech/posts/ios-memos-obsidian-claude](https://drew.tech/posts/ios-memos-obsidian-claude)

Что у него:
- iOS Voice Memo записывает (стандартное приложение Apple)
- macOS Folder Action на `~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings/`
- Shell script конвертирует .m4a → MP3 через ffmpeg
- Загружает в Gemini Flash для транскрипции
- Второй Gemini call: извлекает title, summary, tags
- Пишет markdown файл в Obsidian vault
- Связывает с daily note

Различие у тебя: вместо стандартного Voice Memo (хранится в системной папке) → используешь iOS Shortcut который сохраняет напрямую в `iCloud Drive/Capture/Nous` или `Brain`. Чище, не зависит от системных папок Apple, явный контроль.

### Hints Plugin + Telegram bot
Источник: [forum.obsidian.md/t/how-to-transcribe-a-voice-memo](https://forum.obsidian.md/t/how-to-transcribe-a-voice-memo/101844)

Что у них:
- Telegram bot с командой `/dump`
- Пользователь forwardит сообщение или voice memo боту
- Bot транскрибирует через OpenAI Whisper или Deepgram
- Записывает в Obsidian через Hints Plugin

Различие у тебя: у нас СВОЙ бот (`@nousAGaaSbot`), не сторонний сервис. Полный контроль над тем где сохраняется и как обрабатывается. Цена: $0 (бесплатно через Telegram bot API + Sonnet через нашу подписку).

### Obsidian Vox plugin
Источник: [github.com/vincentbavitz/obsidian-vox](https://github.com/vincentbavitz/obsidian-vox)

Что делает: записывает voice memo прямо в Obsidian app, транскрибирует через локальный whisper.cpp. Хорошо работает на Mac/Linux, на iPhone — не очень (производительность).

Различие у тебя: твой workflow гибрид — capture на телефоне через iOS Shortcut, обработка на VPS через Sonnet. Лучшее из обоих миров: быстрый capture + качественная транскрипция.

---

## ЧАСТЬ 10: Что я сделаю чтобы это всё работало (моё)

После того как ты установишь plugins и iOS Shortcut:

1. **Обновлю `ingest_pending.py`** чтобы он понимал `.m4a` файлы:
   - Если файл .m4a → загрузить в Gemini 2.5 Flash для транскрипции (Gemini лучше с аудио чем Sonnet)
   - Получить транскрипт + summary + entities + actions
   - Сохранить как source page в Obsidian
   - Стоимость: ~$0.01 за минуту аудио

2. **Построю `tools/telegram_poll.py`** (1 час работы):
   - Polling каждые 60 сек на Telegram bot API
   - Если новое сообщение от тебя — сохраняет в нужный vault `raw/pending/`
   - Распознаёт команды `/nous` и `/brain` в forward caption для маршрутизации
   - Поддерживает текст, voice, файлы, фото

3. **Создам `templates/` папку** в каждом vault'е с 5 шаблонами:
   - `templates/source.md`
   - `templates/lesson.md`
   - `templates/audit.md`
   - `templates/entity.md`
   - `templates/project.md`
   - `templates/daily.md`
   - Templater plugin их подхватит автоматически

4. **Создам Dataview queries**:
   - "Все нерешённые блокеры из всех проектов"
   - "Lessons за последнюю неделю"
   - "Audits с status=active"
   - Они будут жить как обычные .md файлы и автоматически обновляться

5. **Setup iOS Shortcut** — могу написать пошагово на твоём iPhone через computer use если хочешь

**Все эти 5 шагов делаю ПОСЛЕ того как ты установишь plugins. Без plugins half of this не работает.**

---

## ЧАСТЬ 11: Чего НЕ делать (распространённые ошибки)

❌ **Не использовать Obsidian Sync ($4/мес)** — у нас уже есть git sync через VPS, бесплатный, работает

❌ **Не путать vault'ы** — Nous (бизнес) и Brain (личное) физически разделены. Если случайно кладёшь личное в Nous — это не utopia

❌ **Не редактировать `raw/pending/` или `raw/processed/` файлы вручную** — они должны быть immutable. Если хочешь изменить — изменяй wiki page, не raw

❌ **Не отключать `ingest_pending.py` cron** — это твой основной канал ingest. Если он не работает, ты теряешь capture

❌ **Не игнорировать lint reports** — раз в неделю проверяй `pages/audits/lint-YYYY-MM-DD.md`. Если есть контрадикции — резолви

❌ **Не использовать Voice Memos системного приложения Apple** — оно сохраняет в скрытую папку, файлы трудно найти. Используй iOS Shortcut который явно сохраняет в iCloud Drive

---

## Сводка: что нужно сделать (чеклист для тебя)

**На Mac (10-15 минут):**
- [ ] Открой Obsidian → Settings → Community plugins → Turn on
- [ ] Установи 4 обязательных plugins (Dataview, Templater, Marp, Daily Notes)
- [ ] Установи 6 дополнительных (Periodic Notes, Tasks, Calendar, QuickAdd, Advanced URI, Omnisearch)
- [ ] Повтори всё для второго vault'а (Brain)

**В Chrome / Safari (5 минут):**
- [ ] Установи Obsidian Web Clipper extension
- [ ] Создай 2 templates: "Nous source" и "Brain source"

**На iPhone (15-20 минут):**
- [ ] Settings → Apple ID → iCloud Drive ON
- [ ] Создай папки `iCloud Drive/Capture/Nous` и `iCloud Drive/Capture/Brain` (с Mac)
- [ ] Открой Shortcuts app → создай "Capture Nous" и "Capture Brain"
- [ ] Добавь оба shortcut'а на Home Screen (большие иконки)
- [ ] Скачай Obsidian iOS app и открой Brain vault

**На Mac (Automator, 10 минут):**
- [ ] Создай 2 Folder Actions для копирования из iCloud Capture папок в `raw/pending/` соответствующих vault'ов

**После всего — скажи мне (Claude Code):**
- [ ] Я обновлю `ingest_pending.py` для аудио (.m4a) поддержки
- [ ] Я построю `tools/telegram_poll.py`
- [ ] Я создам `templates/` папку с 6 шаблонами
- [ ] Я создам начальные Dataview queries для дашбордов

**Время на полный setup:** ~1 час (тебе) + ~3 часа (мне, после твоей установки plugins).

## See also
- [[obsidian-plugins-install-guide-ru]] — детальная пошаговая установка плагинов
- [[vault-model-decision]] — почему 2 vault'а
- [[AUDIT-023-karpathy-llm-wiki-compliance-deep-audit]] — почему этот workflow важен
- [[CLAUDE]] — schema нашего wiki
- Drew Bredvick post: https://drew.tech/posts/ios-memos-obsidian-claude
- Obsidian Vox: https://github.com/vincentbavitz/obsidian-vox
- Obsidian forum voice memo discussion: https://forum.obsidian.md/t/how-to-transcribe-a-voice-memo/101844
