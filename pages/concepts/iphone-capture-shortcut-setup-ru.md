---
type: concept
id: GUIDE-IPHONE-SHORTCUT-RU
title: "iPhone Capture Shortcut — пошаговая установка (RU)"
tags: [guide, iphone, ios, shortcut, capture, ru, setup]
date: 2026-04-07
related: [madi-personal-capture-workflow-ru, madi-workflow-corrections-v2-ru]
language: ru
audience: madi
last_updated: 2026-04-07
source_count: 1
status: reviewed
---
# iPhone Capture Shortcut — пошагово

> Это для тебя на iPhone. Я (Claude) НЕ могу создать iOS Shortcut с Mac — Apple это блокирует. Только ты на телефоне.
>
> Mac-сторона уже готова: iCloud папка `Capture/Nous` создана, courier launchagent запущен (запускается каждые 30 секунд), он автоматически переносит файлы из iCloud в `raw/pending/` твоего vault'а. Тебе осталось ТОЛЬКО создать iOS Shortcut на iPhone.

## Что у тебя должно работать ПЕРЕД началом

✅ iCloud Drive включён на iPhone
   Settings → Apple ID (твоё имя сверху) → iCloud → iCloud Drive → ON

✅ iPhone и Mac на одном Apple ID
   Тот же что и на Mac

✅ Папка Capture/Nous существует в iCloud
   Я её уже создал на Mac. Через ~30 секунд после твоего следующего открытия Files app на iPhone, ты увидишь:
   Files → Browse → iCloud Drive → Capture → Nous

## ЧАСТЬ 1: Простой Shortcut "Capture Voice"

Назначение: тапаешь иконку → запись начинается сразу → говоришь → нажимаешь Stop → файл попадает в iCloud → через 1 минуту на твоём Mac в wiki.

### Шаги (в Shortcuts app на iPhone):

1. **Открой Shortcuts app** на iPhone (фиолетовая иконка)

2. Тап **«+»** в правом верхнем углу

3. Тап **"Add Action"** (большая кнопка по центру)

4. В поиске сверху ищи: **"Record Audio"**

5. Тапни **"Record Audio"** — действие добавлено

6. Тап на действие "Record Audio" чтобы развернуть настройки:
   - **Audio Quality:** Normal (можно High если хочешь файлы больше)
   - **Start Immediately:** ON (важно — иначе придётся тапать ещё раз)
   - **Show Recording Controls:** ON (нужно чтобы видеть Stop button)

7. Тап **«+»** под действием "Record Audio" чтобы добавить следующее действие

8. В поиске: **"Save File"**

9. Тапни **"Save File"** — добавлено

10. На действии "Save File" тапни **"Service"** → выбери **"iCloud Drive"**

11. Тапни **"Destination Folder"** → нажми три точки → выбери **Capture/Nous**

12. **ВЫКЛЮЧИ переключатель "Ask Where to Save"** — иначе будет каждый раз спрашивать куда сохранить

13. Внизу будет поле **"File Name"** — оставь дефолтное **"Recording"** или впиши **"Voice"**. Apple автоматически добавит timestamp.

14. Сверху страницы тапни на название shortcut'а (по умолчанию "Untitled") → переименуй в: **"Capture Voice"**

15. Тапни иконку настроек ⓘ или тап на название shortcut → выбери **"Add to Home Screen"**

16. Выбери иконку (можешь выбрать микрофон или красную точку записи) → название покажется как ты ввёл

17. Тапни **"Add"**

18. Тапни **"Done"** в правом верхнем углу чтобы сохранить shortcut

✅ Готово. Иконка "Capture Voice" на твоём home screen.

### Использование

1. На главном экране iPhone тапни **"Capture Voice"**
2. Запись начинается СРАЗУ (благодаря "Start Immediately")
3. Говори
4. Когда закончил — тап **Stop** в окне записи
5. Файл сохраняется в **iCloud Drive → Capture → Nous**
6. Через ~30 секунд: Mac courier launchagent (`com.nous.capture-courier`) подхватывает файл и копирует в `raw/pending/` твоего Nous vault'а
7. Через ещё ~60 секунд (после того как я обновлю `ingest_pending.py` для аудио): Sonnet/Gemini транскрибирует, создаёт source page в `pages/sources/`
8. Через ~30 секунд: source page синкается обратно на твой Mac, появляется в Obsidian

**Общее время от Stop до полностью обработанной записи в Obsidian: ~2-3 минуты.**

## ЧАСТЬ 2: Альтернативный Shortcut "Capture Photo" (опционально)

Если хочешь захватывать фото документов (визитки, доски, страницы книг):

1. Shortcuts app → **«+»**
2. Add Action → ищи **"Take Photo"** → добавь
3. Add Action → ищи **"Save File"** → выбери Service: iCloud Drive, Folder: Capture/Nous, "Ask Where to Save": OFF
4. Имя: "Capture Photo"
5. Add to Home Screen
6. Готово

## ЧАСТЬ 3: Универсальный Shortcut "Capture Anything" (рекомендую)

Один shortcut который сам спрашивает: голос, фото, или текст.

1. Shortcuts app → **«+»**
2. Add Action → ищи **"Choose from Menu"** → добавь
3. В поле "Prompt" впиши: "Что захватить?"
4. Добавь 3 menu item:
   - "🎤 Voice"
   - "📷 Photo"
   - "📝 Text"
5. Под каждым menu item тапни и добавь действия:
   - **Voice:** Record Audio (Start Immediately ON) → Save File (iCloud Drive / Capture/Nous, Ask OFF)
   - **Photo:** Take Photo → Save File (iCloud Drive / Capture/Nous, Ask OFF)
   - **Text:** Ask for Input (Input Type: Text, Prompt: "Что записать?") → Get Text from Input → Save File (iCloud Drive / Capture/Nous, Ask OFF, File Name: "Note", File Extension: txt)
6. Имя: "Capture"
7. Add to Home Screen с большой иконкой

✅ Один тап на главном экране → выбираешь тип → захватываешь → автоматически в wiki.

## ЧАСТЬ 4: Что НЕ работает / лимиты

❌ **Запись через iOS Shortcut в фоне НЕ работает** — приложение Shortcuts должно быть на экране во время записи. Если ты заблокируешь телефон или переключишься в другое приложение, запись остановится.

✅ **Решение для длинных встреч (>1-2 часа):** используй встроенное Voice Memos приложение Apple (записывает в фоне, файлы синкаются в iCloud автоматически), или Just Press Record ($5 в App Store, тоже фон). После встречи — найди файл в Files → iCloud Drive → переложи руками в Capture/Nous.

✅ **Альтернатива №2:** Otter.ai или Fireflies.ai (платные сервисы которые сами записывают и транскрибируют) — потом forwardишь готовый транскрипт нашему Telegram боту (после того как я построю telegram_poll.py).

## ЧАСТЬ 5: Тест что всё работает (5 минут)

После создания shortcut "Capture Voice":

1. Тапни иконку на home screen
2. Скажи: "Тест один, тест два, проверка записи"
3. Stop
4. Через 30 секунд — открой на Mac Finder → Documents → Projects → Nous AGaaS → Nous → raw → pending
5. Должен увидеть файл вида `2026-04-07_HHMMSS_Recording.m4a`
6. Если файл там — WORKING ✅
7. (После того как я обновлю ingest_pending.py для аудио) — через ещё 1-2 минуты в `pages/sources/` появится транскрибированная source page

Если файл НЕ появился через минуту:
- Проверь что iCloud sync работает на iPhone (Files app → Capture/Nous должен показать твой файл)
- Если в iCloud есть, но в raw/pending нет — мне напиши, я починю Mac courier
- Если в iCloud НЕТ — проверь что в Shortcut "Save File" указан правильный путь iCloud Drive → Capture/Nous

## See also
- [[madi-personal-capture-workflow-ru]] — общий workflow guide
- [[madi-workflow-corrections-v2-ru]] — корректировки V2
- Mac courier script: `/Users/madia/.local/bin/capture_to_nous_pending.sh`
- LaunchAgent: `~/Library/LaunchAgents/com.nous.capture-courier.plist`
