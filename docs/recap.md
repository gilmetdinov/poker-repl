# Recap: состояние проекта poker-repl (rangetool)

## Rangetool: что сделано

Реализованы ADR 001–004 (см. `docs/adr/`):

- **Позиционные hero-ренджи** — конфиг теперь содержит `hero_ranges.BTN/SB/BB`, каждая позиция имеет отдельные `push` и `call` ренджи.
- **Action-aware дерево решений** — команда `hand <label> [open|push|raise|limp]`.
- **EV-прозрачность** — для всех действий решение EV-first. В выводе видны equity, EV (в bb), fold equity, размер ренджа.
- **Автоснятие блайндов** — `Session.next_hand()` вычитает блайнд при *входе* в позицию.
- **Переработка blind_schedule** — `BlindLevel` хранит `bb_chips`; стек пересчитывается при смене уровня.
- **Нелинейная интерполяция** — `interpolation_curve: linear | threshold | sigmoid` и `tight_until_pct`.
- Конфиг и example-файл обновлены; старый формат мигрируется автоматически.

### Исправление парсера `+` (ADR 006, сессия #00003)

Парсер `_expand_non_pair_plus` в `range_parser.py` не соответствовал стандартной покерной нотации:
- **Было:** `KJs+` → только KJs, KQs (менялся кикер, старшая карта фиксирована).
- **Стало:** `KJs+` → KJs, KQs + **все A-high suited** (A2s–AKs). Стандартная нотация: `XY+` = все руки где high ≥ X и если high = X то kicker ≥ Y.

Это системная ошибка, занижавшая все ренджи на 5–10 п.п.

### Инвариант call ⊆ push (ADR 006)

При загрузке конфига `_validate_range_invariants()` проверяет что `call.deep ⊆ push.deep` и `call.wide ⊆ push.wide` для каждой позиции. Нарушение → `ValueError`. Раньше были hands (33 в BTN, KJo/KQo в BB) которые были в call но не в push — это логическая ошибка (open-shove всегда выгоднее колла за счёт fold equity).

### Пересчёт ренджей (ADR 006)

Ренджи пересчитаны для 3-max 15bb на основе push-fold чартов:

| Позиция | Push deep | Call deep | Push wide | Call wide |
|---------|-----------|-----------|-----------|-----------|
| BTN | 30.9% (410c) | 10.4% (138c) | 63.5% | 26.1% |
| SB | 52.3% (694c) | 13.3% (176c) | 64.1% | 28.8% |
| BB | 45.4% (602c) | 23.7% (314c) | 64.1% | 27.9% |

### EV-based override для всех действий (ADR 006)

Раньше только `push` (колл олл-ина) использовал EV-first логику. `open/raise/limp` — чисто range-based, equity игнорировался. Теперь:

- **Все действия** — EV-first. Рендж = консервативный бейзлайн, EV может перебить.
  - `EV > +ev_margin` → PUSH (даже вне ренджа — "overriding conservative range")
  - `EV < -ev_margin` → FOLD (даже в рендже — "-EV despite being in range")
  - `|EV| ≤ ev_margin` → tiebreaker по ренджу
- **Open-shove EV:** `fe × pot + (1-fe) × (equity × total_pot - stack)`
- **Call EV:** `equity × total_pot - stack` (без fold equity)
- Новый параметр `fold_equity` в `thresholds` (default 0.40) — подбирается эмпирически
- В выводе REPL: `EV: +3.96 bb | Fold equity: 40%`
- `Recommendation` dataclass получил поле `ev_bb: float | None`

### Что ещё нужно по ренджтулу

- **Ручное тестирование за столом** — ни разу не тестировался в реальной игре.
- **Калибровка `fold_equity`** — текущий 0.40 — предположение.
- **Вилланский calling range** — сейчас equity считается против playing range оппа, а для open-shove нужно против calling range (который уже playing). Нужен отдельный параметр или эвристика.

---

## Общее

- **Тесты:** 65 проходят (rangetool).
- Все ADR созданы и лежат в `docs/adr/` (001–006, 005 удалён вместе со scraper-модулем).
- `docs/config-report-to-perplexity.md` — отчёт для проверки ренджей через LLM.
- `output/` директории gitignored.
- Ренджтул: ренджи исправлены, парсер починен, EV-first логика работает. Ждёт ручного тестирования.
