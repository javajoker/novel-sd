# DB-01 state-extraction test suite

Five unit tests for the State Extractor. Use the two trap cases (2 and 3) as few-shot
examples in the DB-01 prompt — they fix ~90% of extraction errors. Run a chapter's
extraction against the matching case before trusting the output.

Each case: input prose → expected JSON delta. Pass criteria below each.

---

## Case 1 — Basic combat + consumption (happy path)

**Input:**
> "Ye Fan gritted his teeth and crushed the **Jade Talisman** in his hand. A golden
> shield erupted, blocking the fireball. The impact still threw him back, fracturing
> his **left ribs**. Seeing the enemy reload, he grabbed the **dropped crossbow** from
> the ground."

**Expected:**
```json
{
  "inventory_changes": [
    { "item": "Jade Talisman", "action": "remove", "reason": "consumed/crushed" },
    { "item": "dropped crossbow", "action": "add", "reason": "picked up" }
  ],
  "status_changes": [
    { "type": "injury", "desc": "fractured left ribs", "severity": "medium", "source": "fireball impact" },
    { "type": "buff", "desc": "golden shield", "duration": "temporary" }
  ],
  "knowledge_updates": [],
  "relation_updates": []
}
```
**Pass:** "crushed" = remove; "grabbed" = add; "fractured ribs" = injury.

---

## Case 2 — Metaphor trap (THE most common error)

**Input:**
> "Hearing Lin Rou's betrayal, Ye Fan felt as if a knife had pierced his heart. It was
> colder than any winter snow. He stood frozen, his world shattering like glass."

**Expected:**
```json
{
  "inventory_changes": [],
  "status_changes": [
    { "type": "psychology", "desc": "heartbroken / despair", "value_change": "sanity -20" }
  ],
  "knowledge_updates": [
    { "fact": "Lin Rou betrayed Ye Fan", "source": "dialogue/realization" }
  ],
  "relation_updates": []
}
```
**Pass:** MUST ignore "knife", "pierced", "frozen", "shattering" as literal injuries.
Classify as a psychology change only.

---

## Case 3 — Observation vs. acquisition (window-shopping)

**Input:**
> "Ye Fan peered into the treasure chest. Inside lay the legendary **Dragon Soul
> Sword**, glowing with a red aura. 'Not yet,' he whispered, closing the chest and
> walking away empty-handed."

**Expected:**
```json
{
  "inventory_changes": [],
  "status_changes": [],
  "knowledge_updates": [
    { "fact": "Dragon Soul Sword location", "detail": "inside the chest", "source": "observation" }
  ]
}
```
**Pass:** inventory MUST stay empty. Any `"action":"add"` = FAIL. (He saw it; he didn't
take it.) Note the knowledge gain — he now knows where it is.

---

## Case 4 — Transaction (partial return + gift)

**Input:**
> "Feeling guilty, the little thief handed the **stolen purse** back to Ye Fan. 'I'm
> sorry.' Ye Fan patted the kid's head, sighing. 'Keep the **silver coins** inside,
> just give me the ID token.'"

**Expected:**
```json
{
  "inventory_changes": [
    { "item": "stolen purse (ID token only)", "action": "add", "reason": "returned by thief" },
    { "item": "silver coins", "action": "remove", "reason": "gifted to thief" }
  ],
  "relation_updates": [
    { "subject": "char_ye_fan", "object": "char_little_thief", "predicate": "trusts",
      "action": "create", "properties": { "change": "positive", "reason": "forgiveness / returned item" } }
  ]
}
```
**Pass:** handles "partial return, partial gift" — Ye Fan regains the token but gives
away the coins, and the interaction shifts the relationship positive.

---

## Case 5 — Compound change (cultivation breakthrough / level-up)

**Input:**
> "Boom! The barrier in his dantian shattered. Ye Fan advanced to the **Foundation
> Establishment Stage**. The impurities in his body were expelled as black sludge, and
> his previous **internal injuries** vanished instantly."

**Expected:**
```json
{
  "status_changes": [
    { "type": "rank_up", "desc": "Foundation Establishment Stage", "previous": "Qi Condensation" },
    { "type": "cleansing", "desc": "impurities expelled" },
    { "type": "recovery", "desc": "internal injuries", "action": "remove/healed" }
  ]
}
```
**Pass:** recognises the level-up AND the side effect of clearing existing injuries —
emit all three. ("shattered" here is the dantian barrier breaking = a breakthrough, not
an injury — context matters.)

---

## Mock-data generator (for testing extraction)

To stress-test the extractor, generate a fake chapter synopsis containing: a new
character, a deliberate inconsistency (uses an item lost earlier), and a subtle villain
clue. Run DB-01 on it and confirm it catches the real changes and ignores the noise.
