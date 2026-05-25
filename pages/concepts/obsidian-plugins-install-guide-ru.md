---
type: concept
id: GUIDE-OBSIDIAN-PLUGINS-RU
title: "Obsidian community plugins — пошаговая инструкция установки (RU)"
tags: [guide, obsidian, plugins, ru, dataview, templater, web-clipper, marp, setup]
date: 2026-04-07
related: [AUDIT-023, vault-model-decision]
language: ru
audience: madi
last_updated: 2026-04-07
source_count: 1
status: reviewed
---
# Установка 4 community plugins для Obsidian — пошаговая инструкция

Этот гайд для Mac. Все 4 плагина — бесплатные, официальные, проверенные, рекомендованы Карпати в его LLM Wiki gist. Установка занимает ~10-15 минут на оба vault'а (Nous + Brain).

## Перед началом
- Открой Obsidian.app на Mac
- В левом нижнем углу будет switcher между vault'ами (если у тебя 2 vault'а — Nous и Brain)
- Если ты ещё не открывал Brain vault — кликни на иконку vault switcher и выбери "Open another vault" → "Open folder as vault" → выбери `~/Documents/Brain`

## Включение Community plugins (одноразово)

По умолчанию Obsidian блокирует community plugins ради безопасности. Нужно один раз включить:

1. Открой Obsidian
2. В левом нижнем углу нажми на иконку шестерёнки ⚙️ (Settings)
3. В левой панели выбери **"Community plugins"**
4. Если видишь надпись "Community plugins are currently restricted":
   - Нажми кнопку **"Turn on community plugins"**
   - Появится предупреждение — нажми **"Turn on community plugins"** ещё раз для подтверждения
5. Теперь ты увидишь две вкладки: **"Browse"** и **"Installed plugins"**

## Плагин 1 из 4: Dataview

**Что делает:** позволяет делать SQL-подобные запросы прямо в markdown. Например:
- "Показать все нерешённые блокеры из проектов"
- "Список всех LESSON-XXX за последнюю неделю"
- "Все entity pages с тегом 'partner'"

**Установка:**
1. В Settings → Community plugins → нажми **"Browse"**
2. В поиске сверху введи: `Dataview`
3. Найди плагин **"Dataview"** автора *Michael Brenan* (blacksmithgu)
4. Нажми на него
5. Нажми кнопку **"Install"**
6. После установки — нажми **"Enable"**
7. Готово ✅

**Проверка работы:**
- Создай новую заметку в любом vault'е
- Вставь:
  ```dataview
  TABLE date, status
  FROM "pages/projects"
  ```
- Если видишь таблицу — работает.

---

## Плагин 2 из 4: Templater

**Что делает:** позволяет создавать страницы из шаблонов. Когда ты создаёшь новую entity / lesson / source — Templater автоматически вставляет правильный YAML frontmatter, заголовки, "See also" секцию. Я создам для тебя 5 шаблонов отдельно (entity.md, source.md, lesson.md, audit.md, project.md).

**Установка:**
1. Settings → Community plugins → Browse
2. Найди: `Templater`
3. Автор: *SilentVoid13*
4. Install → Enable

**Конфигурация:**
1. После Enable — в левой панели Settings появится новый раздел **"Templater"**
2. Открой его
3. В поле **"Template folder location"** введи: `templates`
4. Включи переключатель **"Trigger Templater on new file creation"**
5. Готово ✅

(Я создам папку `templates/` со всеми шаблонами в отдельной задаче. Они автоматически появятся когда vault засинкается с VPS.)

---

## Плагин 3 из 4: Obsidian Web Clipper (через браузер)

**Что делает:** браузерное расширение для Chrome/Safari/Firefox. Когда ты читаешь статью в браузере и нажимаешь иконку Web Clipper — статья автоматически конвертируется в markdown и сохраняется в `raw/pending/` нужного vault'а. Дальше наш `ingest_pending.py` подхватывает её и создаёт source page в wiki.

**Это НЕ Obsidian plugin** — это браузерное расширение которое разговаривает с Obsidian через "Obsidian URI scheme".

**Установка (Chrome / Safari):**

### Для Chrome:
1. Открой Chrome
2. Перейди на: https://chromewebstore.google.com/detail/obsidian-web-clipper/cnjifjpddelmedmihgijeibhnjfabmlf
3. Нажми **"Add to Chrome"**
4. После установки — иконка появится справа от адресной строки (синяя с фиолетовым)
5. Нажми на иконку → Settings → Templates
6. Создай новый template для Nous vault:
   - Name: `Nous source`
   - Vault: `Nous` (выбери из dropdown)
   - Folder: `raw/pending`
   - Title: `{{title}}`
   - Content: оставь дефолт
7. Создай второй template для Brain:
   - Name: `Brain source`
   - Vault: `Brain`
   - Folder: `raw/pending`

### Для Safari:
- В Mac App Store найди **"Obsidian Web Clipper"** (бесплатно)
- Установи
- Открой Safari → Settings → Extensions → включи Obsidian Web Clipper
- Дальше та же конфигурация

**Проверка работы:**
- Открой любую статью в браузере (например, https://venturebeat.com/...)
- Нажми иконку Web Clipper → выбери template "Nous source"
- Нажми "Save"
- Через 1-2 минуты файл должен появиться в `~/Documents/Projects/Nous AGaaS/Nous/raw/pending/`
- Через ещё ~1 минуту наш `ingest_pending.py` (cron на VPS, каждую минуту) подхватит его и создаст source page

---

## Плагин 4 из 4: Marp (Marp Slides)

**Что делает:** превращает любую markdown заметку в красивые слайды для презентации. Полезно когда нужно быстро сделать pitch-deck для встречи без открытия PowerPoint / Keynote / Google Slides.

**Установка:**
1. Settings → Community plugins → Browse
2. Найди: `Marp`
3. Найди плагин **"Marp Slides"** (или просто "Marp")
4. Install → Enable
5. Готово ✅

**Использование:**
- Создай заметку с YAML frontmatter:
  ```yaml
  ---
  marp: true
  theme: default
  ---
  # Slide 1
  Content
  ---
  # Slide 2
  Content
  ```
- Открой Command Palette (`Cmd+P`) → введи "Marp" → выбери **"Marp: Open preview"**
- Видишь слайды
- Чтобы экспортировать в PDF: Command Palette → "Marp: Export PDF"

---

## После установки всех 4 — что включится

1. **Dataview** — динамические запросы по wiki. Я смогу писать страницы которые автоматически показывают актуальное состояние ("все нерешённые блокеры из всех проектов") вместо ручного обновления списков.

2. **Templater** — когда ты или я создаём новую entity / source / lesson — frontmatter и структура заполняются автоматически. Меньше ручной работы, меньше расхождений в формате.

3. **Web Clipper** — твой воркфлоу: читаешь статью в браузере → нажимаешь иконку → файл попадает в `raw/pending/` → через минуту наш auto-ingest создаёт source page → ещё через минуту это синкается обратно к тебе на Mac. Полностью замкнутый цикл.

4. **Marp** — за 5 минут можешь сделать слайды для встречи прямо из wiki заметки. Например, брифинг для Сакена ага (markdown версия которого уже в Obsidian: [[saken-aga-netline-briefing-ru]]) можно превратить в презентацию через `marp: true` в frontmatter.

---

## Установить ВО ВСЕХ VAULT'АХ

Все 4 плагина нужно установить **отдельно в каждом vault'е**:

### Vault 1: Nous (`~/Documents/Projects/Nous AGaaS/Nous`)
- Switch на этот vault через vault switcher
- Settings → Community plugins → установи 4 плагина

### Vault 2: Brain (`~/Documents/Brain`)
- Switch на этот vault
- Settings → Community plugins → установи те же 4 плагина

Они независимы — настройки в одном vault'е не влияют на другой.

---

## Troubleshooting

**"Community plugins are currently restricted" не пропадает после "Turn on"**
- Перезапусти Obsidian (Cmd+Q, потом снова открой)
- Если не помогло — открой terminal: `ls "~/Library/Application Support/obsidian/"` чтобы проверить что Obsidian видит vault

**Web Clipper не сохраняет в нужный vault**
- Проверь что в template указан правильный Vault name (как Obsidian его называет в vault switcher)
- Проверь что Folder = `raw/pending` (без слэшей в начале)

**Templater не подхватывает шаблоны**
- Проверь что папка `templates` существует в vault'е
- Restart Obsidian после первой установки

**Dataview запросы не работают**
- Проверь что плагин Enabled (зелёный переключатель)
- Проверь что ты в режиме reading view (Cmd+E переключает edit/reading)

---

## Next steps after installation

1. Сообщи мне в Telegram когда установишь — я создам папку `templates/` со всеми 5 шаблонами
2. Я также создам пример Dataview запроса в `pages/projects/active-blockers-dataview.md` который автоматически показывает все нерешённые блокеры из всех проектов
3. Web Clipper протестируем на одной статье вместе

## See also
- [[AUDIT-023-karpathy-llm-wiki-compliance-deep-audit]] — почему это важно
- [[vault-model-decision]] — двухвалтная архитектура
- [[CLAUDE]] — schema нашего wiki
- Karpathy LLM Wiki gist (origin): https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
