---
type: spec
id: SPEC-BDL-MERGEN-VIOLATION-CARD-2026-04-08
title: "BDL / Mergen 2.0 violation card schema — reverse-engineered from live screenshot (structural, no PII)"
tags: [spec, bdl, mergen, erap, violation-card, schema, reverse-engineering, golden, 2026-04-08]
date: 2026-04-08
source_count: 1
status: reviewed
last_updated: 2026-04-08
priority: p0
related: [bdl-replacement-state-2026-04-07, erap_requirements, phase-3-bdl-replacement-reqs-2026-04-08, source-asylbek-telegram-apr6, LESSON-058-erap-capture-mode]
---

# BDL / Mergen 2.0 violation card — target schema

> **Madi's quote 2026-04-08 evening:** *"3rd image is the way that bdl(mergen) - does the erap official fine, it is inside that was able to get. very important. i think it is golden!"*
>
> **Why golden:** This is the exact field layout of a live, production administrative violation inside the incumbent system (BDL Mergen 2.0 / Риддер instance) that we are replacing. It's the ground truth for what "feature parity with the replaced system" means. Every field here is something ERAP / KPSISU is accustomed to consuming and every dashboard/operator tab is a UX expectation we will have to match or explicitly deprecate.
>
> **PII handling:** The live screenshot contained one real person's data (plate, ИИН, ФИО, DOB, address, etc). **None of that PII is preserved here.** This page stores the STRUCTURAL schema (field names, types, data source, tab layout) only. The actual person's data stays on Madi's phone + in the BDL production DB, not in the wiki. If we need a concrete example for testing, use SYNTHETIC data per [[LESSON-058-erap-capture-mode]].

## Top-of-page header (card-level metadata)

| Field | Type | Example (synthetic) | Source system | Notes |
|---|---|---|---|---|
| Violation ID / Card # | string or int | `MRGN-2025-XXXXXX` | Mergen 2.0 internal | primary key of the card |
| Статус | enum | `На рассмотрении` / `Отправлено в ЕРАП` / `Отклонено` / `Оплачено` | Mergen 2.0 | lifecycle state, drives next-step UI |
| Номер постановления | string | `12345/2026` | auto-generated | administrative decree number, required for fine collection |
| Дата постановления | date | `08.04.2026` | auto | the `created_at` of the card |

## Tab 1 — Нарушение (violation details) — PRIMARY TAB

This is the tab shown in the screenshot. It contains the core facts of the violation — what, where, when, by whom's vehicle, with what evidence.

### Section: Plate + violation type

| Field | Type | Example (synthetic) | Source |
|---|---|---|---|
| ГРНЗ (State reg plate) | string | `AAA 123 01` | camera OCR + manual confirm |
| Страна регистрации | ISO or text | `Казахстан` | plate OCR + lookup |
| Вид нарушения | enum / text | `Превышение скорости` / `Проезд на красный` / `Выезд на встречную` / `Езда по разделительной` | rule engine classifying sensor event |
| Статья КоАП | string | `ст. 592 ч.1 КоАП РК` | rule engine mapping violation type → article |
| Сумма штрафа | currency / int | `26240 ₸` | КоАП schedule lookup keyed on article + severity |

### Section: Sensor measurement (what the camera saw)

| Field | Type | Example (synthetic) | Source | Notes |
|---|---|---|---|---|
| Фактическая скорость | int km/h | `115` | camera radar | measured |
| Установленный лимит | int km/h | `60` | road segment metadata | from road registry by GPS |
| Погрешность | int km/h | `2` | camera spec | sensor error margin, subtracted for legal defensibility |
| Полоса | int | `2` | camera segmentation | which lane the violation was on |
| Направление движения | enum | `В сторону центра` | camera orientation metadata | |

### Section: Location + time

| Field | Type | Example (synthetic) | Source |
|---|---|---|---|
| Место нарушения | string | `ВКО, г. Усть-Каменогорск, ул. Независимости, 12` | reverse-geocoded from camera GPS |
| Координаты (GPS) | lat,lng | `49.9494, 82.6278` | camera metadata |
| Камера (АПК ID) | string | `APK-UKG-042` | MRGN ↔ camera mapping |
| Дата и время события | datetime | `08.04.2026 14:32:07` | camera timestamp, Asia/Almaty |
| Посольский знак / дипстатус | bool | `нет` | plate lookup against MFA diplomatic list |

## Tab 2 — Транспортное средство (vehicle registry)

Data pulled from the central vehicle registry (СР ТС / СРТС) keyed by plate number.

| Field | Type | Example (synthetic) | Source |
|---|---|---|---|
| ГРНЗ | string | `AAA 123 01` | same as Tab 1 |
| Номер СРТС | string | `КЗ №XXXXXXX` | vehicle registry |
| VIN | string | `XXXXXXXXXXXXXXXXX` | vehicle registry |
| Марка | string | `Toyota` | vehicle registry |
| Модель | string | `Camry` | vehicle registry |
| Цвет | string | `Белый` | vehicle registry |
| Год выпуска | int | `2018` | vehicle registry |
| Категория | enum | `B` | vehicle registry |
| Дата выдачи СРТС | date | `01.03.2020` | vehicle registry |
| Страховой полис (ОСАГО) | string | `OSK-YYYY-XXXXXX` | insurance registry |
| Дата техосмотра | date | `15.06.2025` | техосмотр registry |
| Дата следующего техосмотра | date | `15.06.2027` | calculated |

## Tab 3 — Владелец (vehicle owner)

Data pulled from the national personal registry keyed by ИИН looked up via plate.

| Field | Type | Example (synthetic) | Source |
|---|---|---|---|
| Резидент РК | bool | `да` | МИД registry |
| ИИН | 12-digit string | `XXXXXXXXXXXX` | vehicle registry → personal registry |
| ФИО | string | `Ivanov Ivan Ivanovich` | personal registry |
| Дата рождения | date | `DD.MM.YYYY` | personal registry |
| Пол | enum | `М` / `Ж` | personal registry |
| Национальность | string | `Казах` | personal registry |
| Место рождения | string | `VKO` | personal registry |
| Место работы | string | `ТОО ...` | employer registry (may be empty) |
| Телефон | string | `+7 XXX XXX XX XX` | personal registry (may be empty) |

## Tab 4 — Адрес регистрации (registered address)

| Field | Type | Source |
|---|---|---|
| Область | string | personal registry |
| Город / район | string | personal registry |
| Улица | string | personal registry |
| Дом | string | personal registry |
| Квартира | string | personal registry |
| Индекс | string | derived |

## Tab 5 — Документ (identity document)

| Field | Type | Source |
|---|---|---|
| Тип документа | enum (`Удостоверение личности` / `Паспорт`) | personal registry |
| Номер документа | string | personal registry |
| Дата выдачи | date | personal registry |
| Кем выдан | string | personal registry |

## Tab 6 — Фото / Видео (evidence)

| Field | Type | Source | Notes |
|---|---|---|---|
| Фото номерного знака | image | camera ISAPI event attachment | OCR-confirmable crop |
| Общее фото ТС | image | camera ISAPI event attachment | full-vehicle view |
| Обзорное видео (короткий clip) | mp4 / jpg sequence | camera ISAPI event attachment | 3-5 second pre/post event |
| Калибровочная метка | overlay on image | rendered at display time | showing radar beam, speed overlay, plate rectangle |

## Tab 7 — Оплата (payment status)

| Field | Type | Example (synthetic) | Source |
|---|---|---|---|
| Статус оплаты | enum | `Не оплачено` / `Оплачено` / `Частично` / `Просрочено` | payment gateway |
| Дата оплаты | datetime or null | | payment gateway |
| Сумма оплачена | currency | | payment gateway |
| Платежный документ | string | | payment gateway |
| Скидка применена | bool | | calculated (7-day 50% discount rule) |

## Tab 8 — ОПМ (Оперативно-профилактические мероприятия)

Operational-preventive measures — historical context for the vehicle/owner. Mostly informational for the reviewer.

| Field | Type | Source |
|---|---|---|
| Список прошлых нарушений | table | this same registry, filtered by owner ИИН |
| Оперативные ориентировки | list | police databases (stolen, wanted, etc) |
| Флаг "в розыске" | bool | МВД stolen-vehicle registry |

## Tab 9 — История (audit trail)

Append-only log of what happened to this card over its lifecycle.

| Column | Type | Example |
|---|---|---|
| Timestamp | datetime | `08.04.2026 12:52:03` |
| Действие | enum | `Создано` / `Отправлено на согласование` / `Отправлено в ЕРАП` / `Статус изменен` / `Комментарий добавлен` |
| Пользователь | string | operator username or `system` |
| Комментарий | text (optional) | |

## Tab 10 — Документ (administrative decree PDF)

Final step: the rendered PDF of the official постановление that gets sent (1) to ЕРАП via the SmartBridge pipeline, and (2) to the vehicle owner's registered address for collection.

| Field | Type | Source |
|---|---|---|
| Номер постановления | string | same as card header |
| PDF rendered | file | Mergen template engine |
| Signature (ЭЦП) | bytes | operator or system ЭЦП (ГОСТ 34.311-95) |
| Status | enum | `Черновик` / `Подписано` / `Отправлено в ЕРАП` |

## Implications for Satory VKO implementation

This schema is what we must match (or explicitly decide to deprecate parts of) for Satory VKO to be a drop-in BDL replacement. Mapping each tab to our existing or planned components:

| BDL tab | Satory VKO source | Status | Action |
|---|---|---|---|
| Нарушение (core) | camera ISAPI event + rule engine | 🟡 Backend skeleton 75% | [[phase-3-bdl-replacement-reqs-2026-04-08]] REQ-090/091 |
| Транспортное средство | vehicle registry lookup | 🔴 Not yet integrated | new REQ needed — integrate with ГБД ФЛ/ЮЛ |
| Владелец | personal registry lookup | 🔴 Not yet integrated | new REQ needed — ИИН lookup |
| Адрес регистрации | same as Владелец | 🔴 Not yet integrated | same REQ |
| Документ (identity) | same as Владелец | 🔴 Not yet integrated | same REQ |
| Фото / Видео | ISAPI event attachments | 🟡 Captured but not served in UI | UI work in `satory-nextjs` |
| Оплата | payment gateway integration | 🔴 Not yet designed | future phase — after core pipeline works |
| ОПМ | historical card lookup | 🔵 Trivial once core DB is populated | do after first 100 cards are in DB |
| История | audit log table | 🟢 Exists in our DB | bind to UI |
| Документ (decree PDF) | template engine | 🔴 Not yet designed | new REQ — PDF rendering + ЭЦП signing |

## Open questions for next session with Madi / Asyl / Daniyar

1. **Vehicle + owner registry access** — how does BDL access the ГБД ФЛ registry? Via SmartBridge (different service than ERAP) or direct contract with МИД / ЦОН? This is a second integration surface we haven't scoped yet.
2. **PDF decree rendering** — is there a template we must use, or can we design our own as long as required fields are present? What are the font/layout/ЭЦП signature-block requirements?
3. **Payment integration** — which gateway does BDL use? Is that a separate decision for Satory or inherited?
4. **Status transitions** — are the status transitions (e.g., `На рассмотрении → Отправлено в ЕРАП`) gated by an operator click, or automatic? Some violations may require human review (e.g., plate OCR confidence below threshold).
5. **Camera ↔ card binding** — is the MRGN identifier enough to reconstruct which physical camera triggered which card, or does BDL attach more metadata (sensor firmware version, calibration date) for legal defensibility?

## How to use this page

- **When implementing new Satory VKO modules**, read the relevant tab schema here first — don't reinvent field names; match BDL for drop-in replacement unless there's a reason to deprecate.
- **When talking to KPSISU / Asyl / Denis**, use this as the structural reference so everyone agrees on what data we must preserve.
- **When writing new REQs for the factory**, link back to this spec so the implementation matches ground truth.

## See also
- [[bdl-replacement-state-2026-04-07]] — canonical BDL-replacement state + blockers
- [[erap_requirements]] — ERAP-side requirements
- [[phase-3-bdl-replacement-reqs-2026-04-08]] — REQ-090 to REQ-105 work queue
- [[source-asylbek-telegram-apr6]] — Asyl's original BDL context + screenshots
- [[LESSON-058-erap-capture-mode]] — rule: capture structure, not PII
- [[shep-submission-confirmed-2026-04-08]] — the ШЭП milestone on the same day
- [[shep-client-registration-2026-04-08]] — ШЭП form spec
- [[AUDIT-029-three-vpns-reconciled-camera-nit-firewall]] — VPN state
