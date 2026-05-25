---
type: concept
id: GUIDE-MADI-WORKFLOW-V2-RU
title: "Личный workflow Мади V2 — корректировки + точные имена плагинов (RU)"
tags: [guide, workflow, ru, obsidian, corrections, v2]
date: 2026-04-07
related: [madi-personal-capture-workflow-ru, AUDIT-023, vault-model-decision]
language: ru
audience: madi
supersedes: madi-personal-capture-workflow-ru
last_updated: 2026-04-07
source_count: 1
status: reviewed
---
# Workflow V2 — корректировки после твоих вопросов

> Это **поправка** к [[madi-personal-capture-workflow-ru]]. Не дублирует, дополняет и исправляет.

## 1. У тебя ОДИН vault, не два

Подтверждено через `~/Library/Application Support/obsidian/obsidian.json`:

- **Nous vault** — `~/Documents/Projects/Nous AGaaS/Nous` — `open: true` — это единственный vault который ты видишь и используешь
- **Brain vault** — `~/Documents/Brain` — `open: false` — существует на диске, я его создал, ты НИКОГДА не открывал

**Решение:** оставляем Brain «спящим» на диске. Он не мешает, занимает 0 места в твоей рабочей жизни. Если когда-нибудь захочешь начать отдельно вести личное — клик в Vault Switcher и он там. До этого момента — игнорируем.

**Для личных заметок (если когда-то понадобится):** создаём подпапку `pages/personal/` ВНУТРИ Nous vault. Один vault, тематические подпапки. Karpathy-compliant, проще чем два vault.

**Все инструкции ниже — для одного vault (Nous).**

## 2. Точные имена плагинов (двойная проверка)

### 2 плагина которые ты ещё не установил

| Плагин | Точное имя в Browse | Автор | Тип |
|---|---|---|---|
| **Marp Slides** | "Marp Slides" (со словом Slides) | samuele-cozzi | Community plugin |
| **Daily Notes** | НЕ COMMUNITY — это CORE plugin Obsidian | Obsidian (встроенный) | Core plugin |

**Marp Slides** — установка:
1. Settings → Community plugins → Browse
2. Поиск: `Marp Slides` (именно с "Slides")
3. Автор: **samuele-cozzi**
4. GitHub: https://github.com/samuele-cozzi/obsidian-marp-slides
5. Install → Enable

**Daily Notes** — это НЕ нужно искать в Browse, оно уже встроено в Obsidian:
1. Settings → **Core plugins** (отдельный раздел, выше Community plugins!)
2. Найти "Daily notes" в списке
3. Включить переключатель
4. Готово — никаких загрузок, никаких поисков

### Двойная проверка остальных 8 плагинов

В Settings → Community plugins → **Installed plugins** ты должен видеть эти 8 с правильными авторами:

| # | Имя | Автор | Зачем |
|---|---|---|---|
| 1 | Dataview | blacksmithgu | Динамические запросы по wiki |
| 2 | Templater | SilentVoid13 | Шаблоны страниц |
| 3 | Periodic Notes | Liam Cain | Расширяет Daily Notes до weekly/monthly/yearly |
| 4 | Tasks | obsidian-tasks-group (Clare Macrae) | Task management через `- [ ]` |
| 5 | Calendar | Liam Cain | Календарь сбоку |
| 6 | QuickAdd | chhoumann | Быстрые шаблонные кнопки |
| 7 | Advanced URI | Vinzent03 | URI-схема для Obsidian (нужна для iOS Shortcuts) |
| 8 | Omnisearch | scambier | Полнотекстовый поиск (лучше чем дефолтный) |

Если у какого-то плагина другой автор — это другой плагин, удали и установи правильный.

## 3. Claude Code в Obsidian — НОВОЕ, важное

То что делают другие про-юзеры (Karpathy включительно): они подключают Claude Code напрямую к Obsidian через MCP.

**Плагин:** **Claude Code MCP** ([iansinnott/obsidian-claude-code-mcp](https://github.com/iansinnott/obsidian-claude-code-mcp), 233 stars)

**Что он даёт:**
Я смогу читать и редактировать твой wiki **прямо из этого чата** без ssh, grep, git commit. Например:
- Ты пишешь заметку в Obsidian, я её вижу в реальном времени
- Я могу создавать новые страницы и они появляются у тебя сразу
- Я могу делать surgical edits существующих страниц

**Установка:**
1. Settings → Community plugins → Browse
2. Поиск: `Claude Code MCP`
3. Автор: **iansinnott**
4. Install → Enable
5. Перезапустить Claude Code (НЕ эту сессию, следующую)
6. В новой сессии Claude Code: набери `/ide` → выбери "Obsidian"

**После установки — что я смогу делать:**
- `view` — читать любой файл в твоём vault
- `str_replace` — точечные правки
- `create` — создавать новые файлы
- `insert` — добавлять в файл
- `get_current_file` — видеть какой файл ты сейчас редактируешь
- `get_workspace_files` — список всего в vault

**Это НЕ заменяет qmd MCP** который мы установили вчера — qmd для быстрого hybrid search, claude-code-mcp для read/write. Они работают вместе.

### Альтернативы которые я рассмотрел и отверг

- **Smart Connections** by brianpetro — chat-with-notes UI внутри Obsidian. Не нужно: ты уже общаешься со мной через Claude Code, лучше.
- **Copilot for Obsidian** by logancyang — то же самое что Smart Connections, требует свой API key.
- **Infio Copilot** — Cursor-style autocomplete внутри Obsidian, для написания текстов. Другая задача.

**Ставим только Claude Code MCP. Остальное игнорируем.**

## 4. iPhone Default new note location — точные шаги

Ты не нашёл это потому что на iOS меню называется иначе:

1. Открыть Obsidian app на iPhone
2. Открыть Nous vault если ещё не открыт
3. **Тапнуть три горизонтальные линии (≡) внизу справа** → откроется левая боковая панель
4. **Тапнуть иконку шестерёнки ⚙️ внизу слева** этой панели
5. Прокрутить вниз до раздела **"Files & Links"**
6. Тапнуть **"Files & Links"**
7. Найти **"Default location for new notes"**
8. Три варианта:
   - "Vault folder" (корень)
   - "Same folder as current file"
   - **"In the folder specified below"** ← выбрать ЭТО
9. Ниже появится **"Folder to create new notes in"** → тапнуть → ввести: `raw/pending`
10. Done / назад

Теперь когда тапнешь **+** в Obsidian iPhone, новая заметка создаётся в `raw/pending/` и `ingest_pending.py` подхватывает её через минуту.

## 5. Option A vs Option B — для встреч >30 минут

**ОТВЕТ: Option A (iCloud + iOS Shortcut) выигрывает для встреч любой длины. Option B (Telegram bot) — для коротких текстовых форвардов.**

### Жёсткое сравнение

| Параметр | Option A: iCloud + Shortcut | Option B: Telegram bot |
|---|---|---|
| **Лимит длины записи** | НЕТ — только память телефона (часы) | ДА — Telegram bot file limit 50 MB ≈ 45-50 мин аудио |
| **Качество звука** | Полное (M4A AAC, настраиваемое) | Сжатое Telegram (OGG opus, ниже) |
| **Надёжность** | Local-first. iCloud синкается когда есть сеть. Работает оффлайн. | Нужен интернет во время записи |
| **Приватность** | Аудио не уходит к третьим лицам пока ты не выберешь ingest | Идёт через серверы Telegram (под российским контролем формально) |
| **Future-proof** | Apple iCloud — гарантированно работает 10+ лет | Telegram bot tokens могут быть отозваны, политика меняется |
| **Время setup** | 25-30 минут одноразово | 5 минут + я строю polling tool (~1 час) |
| **Стоимость** | $0 (5GB iCloud free tier) | $0 |
| **Работает для встреч 2-3 часа (board meetings)** | **ДА, без ограничений** | **НЕТ**, упирается в 50 MB Telegram cap |
| **Работает для коротких 10-сек записей** | ДА | ДА |
| **Bulletproof — работает 100% времени** | ДА если iCloud настроен | НЕТ — зависит от Telegram + bot uptime + моего polling script |

**Вердикт:** Option A — основной канал. Option B — convenience дополнение для текстовых пересылок.

**Я строю ОБА**, но Option A — это позвоночник.

## 6. Зачем iCloud Drive + Capture папки + iOS Shortcut?

**Польза одной фразой:** записал на телефоне → через 2 минуты в wiki, расшифровано, проиндексировано, ищется. **Один тап на телефоне, ноль печатания, ноль форвардов.**

### Почему именно эта архитектура (фундаментальная проблема)

**iOS приложения НЕ могут писать напрямую в Mac папку.** iPhone в песочнице. Apps могут писать только в свой контейнер ИЛИ в iCloud Drive (благословлённое Apple cross-device хранилище).

### Цепочка

```
[Тап "Capture Nous" иконка на iPhone]
        ↓
[iOS Shortcut записывает аудио]
        ↓
[Сохраняет в iCloud Drive: Capture/Nous/2026-04-08-1530.m4a]
        ↓ (Apple синкает на Mac за 5-30 сек)
[Файл появляется в: ~/Library/Mobile Documents/com~apple~CloudDocs/Capture/Nous/]
        ↓
[Mac Folder Action (Automator) видит новый файл]
        ↓ (запускает shell script)
[Копирует в: ~/Documents/Projects/Nous AGaaS/Nous/raw/pending/]
        ↓ (1 минуту, авто-sync на VPS)
[VPS видит файл в raw/pending/]
        ↓ (ingest_pending.py cron)
[Sonnet или Gemini транскрибирует + извлекает entities + создаёт source page]
        ↓
[Source page синкается обратно на твой Mac]
        ↓
[Видишь это в Obsidian]
```

### Зачем каждый шаг

- **iCloud Drive bridge**: единственный способ для iPhone общаться с Mac для доставки файлов
- **Automator Folder Action**: iCloud Drive не в твоём wiki path. Action — курьер который копирует файл туда где живёт wiki
- **`raw/pending/`**: convention из Karpathy LLM Wiki — drop zone для необработанных источников
- **`ingest_pending.py` cron**: авто-summarizer который превращает сырой файл в структурированную страницу
- **Bidirectional git sync**: твой Mac и VPS остаются в lockstep, новая wiki page появляется на обоих

### В простых словах

- **Без этого setup**: записал встречу → файл застрял в телефоне → через 3 дня забыл его перенести → context потерян навсегда
- **С этим setup**: записал встречу → через 2 минуты транскрибировано и проиндексировано → когда спросишь меня "что Сакен ага говорил про NetLine pricing?" — нахожу мгновенно через qmd

**Это самое близкое к "встреча сама себя записывает в твой второй мозг" что существует сегодня.**

## 7. Telegram bot polling — детально что я построю

**Когда:** после того как ты установишь Obsidian plugins. ~1 час моей работы.

**Архитектура:**
```
[Ты пересылаешь сообщение @nousAGaaSbot]
   ↓
[Telegram сохраняет у себя]
   ↓ (каждые 60 сек)
[VPS cron: tools/telegram_poll.py]
   ↓ (вызывает Telegram API getUpdates — это БЕСПЛАТНО)
[Парсит новые сообщения, читает caption для routing]
   ↓
[Пишет в raw/pending/telegram-2026-04-08-1530-from-asyl.md]
   ↓
[ingest_pending.py подхватывает на следующей минуте]
   ↓
[Source page в wiki]
```

**Функциональность:**
- Polls Telegram каждые 60 сек через HTTP — БЕСПЛАТНО, никаких LLM tokens
- Поддерживает: текст, голосовые, фото, документы, forwarded messages
- Caption-based routing: `/nous` (по умолчанию) или `/brain`
- Извлечение тегов из caption: `/nous from-asyl smartbridge` → теги `from-asyl`, `smartbridge`
- Голосовые: скачивание → ingest_pending.py транскрибирует через Gemini
- Файлы (PDF, DOCX): скачивание → ingest_pending.py извлекает текст
- Resilient: если telegram_poll умирает, файл остаётся на Telegram сервере, retry на следующем цикле
- **Стоимость: $0 polling, $0.01-0.05 за ingested сообщение (только LLM часть)**

### Примеры использования (после того как построю)

**Голосовая заметка пока ведёшь машину:**
1. Telegram → @nousAGaaSbot
2. Hold микрофон → говоришь → отпускаешь
3. Caption: `/nous voice-note`
4. Send
5. ~2 минуты позже — расшифровано в твоём wiki

**Forward важное сообщение из другого чата:**
1. Long-press сообщение в любом Telegram chat
2. Forward → @nousAGaaSbot
3. Caption: `/nous from-asyl urgent`
4. Send
5. ~2 минуты позже — в твоём wiki с тегами `from-asyl` + `urgent`

**Forward PDF который кто-то прислал:**
1. Forward файл → @nousAGaaSbot
2. Caption: `/nous spec`
3. Send
4. ~2 минуты позже — текст извлечён, entities определены, в твоём wiki

**ВАЖНО:** для встреч >30 минут — ИСПОЛЬЗУЙ Option A. Telegram cap 50 MB.

## 8. Mac Claude Code: Opus или Sonnet?

| Задача | Модель | Почему |
|---|---|---|
| Длинные agentic сессии типа этой | **Opus 4.6** | Лучший reasoning, ты строишь бизнес-стратегию |
| Быстрые правки файлов / lookups | **Sonnet 4.6** | В 5 раз дешевле, быстрее, более чем достаточно |
| Фабрика на VPS (уже настроено) | **Sonnet 4.6** | После AUDIT-022 swap |
| Поиск по wiki в чате | **qmd через MCP** | Уже подключено вчера, быстро, бесплатно |
| Read/write vault в чате | **claude-code-mcp через Obsidian плагин** | Установить сегодня |

**Как переключаться между Opus и Sonnet в Claude Code:**
- В чате набери `/model` → меню → выбери Opus или Sonnet
- Или per-session: `claude --model sonnet` или `claude --model opus`

**Для твоего проекта:**
- **Ежедневное использование**: Sonnet (дёшево, быстро)
- **Жёсткие стратегические решения / составление документов / бизнес-звонки**: Opus
- **Можно переключаться в середине разговора**

## 9. raw/ folder cleanup — сделано

Было messy. Я почистил.

**Было** (loose файлы на верхнем уровне):
- 2 m4a recordings
- 1 пустой Untitled.md
- 3 loose .md файла

**Стало:**
```
raw/
├── README.md
├── asylbek-apr6/         (PDFs, XMLs из Asylbek)
├── legal/
├── meetings/             (все .md встречи)
├── pending/              (auto-ingest watch folder)
├── processed/            (post-ingest archive)
├── recordings/           (НОВОЕ — m4a аудио)
├── specs/
├── state-snapshots/      (НОВОЕ — master state snapshots)
├── team/
├── telegram/             (НОВОЕ — copy-pasted Telegram messages)
└── transcripts/
```

Все wikilinks в source pages обновлены на новые пути. Через ~2 минуты синкается на твой Mac.

## Полный чеклист для Madi (что делать)

### Сейчас (10-15 минут):
- [ ] Settings → **Core plugins** → включить **Daily notes**
- [ ] Settings → Community plugins → Browse → найти **Marp Slides** (samuele-cozzi) → Install → Enable
- [ ] Settings → Community plugins → Browse → найти **Claude Code MCP** (iansinnott) → Install → Enable
- [ ] Проверить что 8 других плагинов установлены с правильными авторами (см. таблицу выше)

### iPhone (5 минут):
- [ ] Open Obsidian on iPhone → ≡ → ⚙️ → Files & Links → Default location for new notes → "In the folder specified below" → `raw/pending`

### Перезапустить Claude Code (НЕ эту сессию):
- [ ] Закрыть текущую Claude Code сессию (или пусть закончится)
- [ ] Открыть новую → набрать `/ide` → выбрать "Obsidian"
- [ ] После этого я смогу читать/писать твой vault напрямую

### Скажи мне когда готово — я сделаю:
- [ ] Обновлю `ingest_pending.py` для .m4a аудио (Gemini Flash транскрипция)
- [ ] Построю `tools/telegram_poll.py` (1 час)
- [ ] Создам `templates/` папку с 6 шаблонами для Templater
- [ ] Создам Dataview queries для дашбордов
- [ ] Помогу с iOS Shortcut + Automator Folder Action setup (через computer use если хочешь)

## See also
- [[madi-personal-capture-workflow-ru]] — оригинальный гайд (этот файл его дополняет)
- [[obsidian-plugins-install-guide-ru]] — детальная инструкция установки плагинов
- [[AUDIT-023-karpathy-llm-wiki-compliance-deep-audit]]
- Karpathy LLM Wiki gist: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Claude Code MCP plugin: https://github.com/iansinnott/obsidian-claude-code-mcp
- Marp Slides: https://github.com/samuele-cozzi/obsidian-marp-slides
