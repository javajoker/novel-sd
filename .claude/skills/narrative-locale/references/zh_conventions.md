# 中文网络小说写作约定 (Chinese web-fiction pack)

Conventions for writing a novel in Chinese (`language: zh-Hans` 简体 or `zh-Hant` 繁體).
All structural KB fields stay ASCII (see the bilingual rule); everything below governs
the *content* the phases generate.

---

## 1. 题材 (Genres)

The dominant Chinese web-fiction (网文) genres and their load-bearing tropes:

| 题材 | Pinyin | English gloss | Core engine |
|---|---|---|---|
| 玄幻 | xuánhuàn | eastern fantasy | invented cosmology + power ladder; 升级流 (level-up) |
| 仙侠 | xiānxiá | immortal heroes | 修真/修仙 cultivation toward immortality; 渡劫 tribulations |
| 武侠 | wǔxiá | martial heroes | 江湖, sects, 内功/招式; lower-magic, honour-driven |
| 都市 | dūshì | urban | modern city; hidden powers / business / 装逼打脸 |
| 系统 | xìtǒng | system | a game-like "system" grants quests/rewards to the MC |
| 穿越 | chuānyuè | transmigration | MC sent to another world/era, keeps modern knowledge |
| 重生 | chóngshēng | rebirth | MC reborn into the past, replays life with foreknowledge |
| 科幻 | kēhuàn | sci-fi | 星际/末世/机甲 |
| 言情 | yánqíng | romance | relationship arc is primary |

Record the chosen genre in `source.genre`. Genre dictates the power system (below),
the pacing expectations, and the reader's 期待 (what payoff they're promised).

---

## 2. 力量体系 / 境界 (Power systems & cultivation realms)

仙侠/玄幻 run on a **境界 (realm) ladder** — a strictly ordered hierarchy the MC climbs.
Encode each tier as an entity (`subtype: concept`) AND as ordered world-rule triples so
narrative-consistency can enforce rank:

```json
{ "id": "rule_realm_01", "source": "筑基", "relation": "RANKS_HIGHER_THAN",
  "target": "炼气", "scope": "hierarchy", "note": "筑基期高于炼气期" }
```

A classic 修真 ladder (customise per novel — the *names* are the author's worldbuilding):

`炼气 → 筑基 → 金丹 → 元婴 → 化神 → 炼虚 → 合体 → 大乘 → 渡劫`

Each realm typically has 早期/中期/后期/巅峰 (early/mid/late/peak) sub-stages. Key rules
the consistency guard should hold:

- A character cannot use an ability above their current 境界 (`prerequisites` of an event
  reference the needed realm; paradox guard checks the as-of-chapter state).
- 突破 (breakthrough) is a `status.type: rank_up` delta — and per the extraction tests it
  often clears existing injuries (`recovery`).
- 灵根 (spiritual root / talent) gates which 功法 (techniques) a character can learn —
  encode as a world rule (e.g. `(火灵根)-[CONFLICTS_WITH]->(水系功法)`).

武侠 uses 内力/内功 depth and named 武功招式 rather than realms; 系统 uses 等级/经验.

---

## 3. 命名约定 (Naming)

Generate names in Chinese; keep the ASCII `id` as the pinyin slug.

- **人物 (people):** 2–3 characters, surname + given (叶凡, 林柔, 萧炎). Villains/elders
  often get titles (魔尊, 莫长老). Store `canonical_name: "叶凡"`, `id: "char_ye_fan"`,
  `attributes.pinyin: "Yè Fán"`, plus 称号/外号 in `aliases` (["叶天帝", "小凡"]).
- **门派/势力 (sects/factions):** 剑宗, 血煞门, 天音阁, 万兽山庄. `id: "elem_jian_zong"`.
- **功法/招式 (techniques/skills):** evocative 4-char names — 九天剑诀, 焚天炼气诀,
  破军斩. Store as `Object`/`Concept` entities or character abilities.
- **地点 (places):** 黑风寨, 北玄域, 落日山脉. `id: "elem_hei_feng_zhai"`.
- **物品 (items):** 噬魂剑, 九转还魂丹, 储物戒. `subtype: item`.

When the same person has many forms (本名/道号/称号), the most complete is
`canonical_name`, the rest are `aliases` — the merger/search treat aliases as the same
entity.

---

## 4. 连载结构与节奏 (Serial structure & pacing)

Chinese web novels are serialised daily; structure follows reader-retention norms:

- **黄金三章 (the golden first three chapters):** the opening 3 chapters must hook —
  establish the MC's 困境 (plight), a clear 金手指 (cheat/advantage), and the first small
  payoff. narrative-architect should front-load a 爽点 here.
- **爽点 (gratification beats):** regular payoff moments — 打脸 (face-slapping a scornful
  rival), 升级 (breakthrough), 获得宝物 (gaining treasure), 扮猪吃虎 (hiding strength then
  winning). Plan a cadence of these in the beat sheets; long gaps lose readers.
- **卷 / 章 (volumes / chapters):** a 卷 is an arc (e.g. 宗门篇, 秘境篇); chapters are
  ~2000–4000 字 each. Map to `vol_*` / `ch_*` in the outline tree.

  **Minimum chapters per volume by novel length tier** (enforced by narrative-architect):

  | 体量 | `source.tier` | 典型总字数 | 每卷章节下限 | 备注 |
  |---|---|---|---|---|
  | 短篇 | `short_story` | < 5万字 | 无卷结构 | 整篇一卷或直接分场景，无需 vol_* |
  | 中篇 | `novella` | 5–20万字 | 10 章 / 卷 | 1–2 卷即可；单卷亦可 |
  | 长篇 | `novel` | 20–100万字 | 30 章 / 卷 | 3–5 卷；每卷有独立弧线 |
  | 超长篇 / 网文连载 | `long_novel` | 100万字以上 | **80 章 / 卷（硬下限）** | 读者期待每卷充足的爽点积累与高潮；不足 80 章须合卷或补充事件密度 |

  When planning a volume that falls short, either expand the event graph or fold the arc
  into an adjacent volume — do not mark `status: planned` until the floor is met.
- **百万字 (million-character) novels:** "million words" in Chinese means **百万字**
  (characters). The memory tooling counts CJK characters ~1 token each, so a 百万字 novel
  is well past any context window — this is exactly why the chapter-masked profile +
  search exist. Word-count targets in `target_word_count` are in 字.
- **钩子 (hooks) / 卡章:** end chapters on a 悬念 (cliffhanger). Track unresolved hooks in
  `memory/plot_threads.json` (开坑/填坑 = open/close a loop).

---

## 5. 抽取陷阱 (DB-01 extraction traps in Chinese)

The state extractor must read Chinese prose; the same metaphor/observation traps apply,
in Chinese form:

- **成语/比喻 (idioms & metaphors) ≠ physical events.** "心如刀绞" (heart twisted like a
  knife) = psychology, NOT injury. "肝肠寸断", "万箭穿心", "如坠冰窖" are emotional. Ignore
  the physical words.
- **看/望/瞧 (observe) ≠ 拿/取/捡/夺 (acquire).** "他看了一眼宝剑" = no inventory change;
  "他捡起宝剑" / "他夺过宝剑" = add. Window-shopping rule, in Chinese.
- **突破 (breakthrough) vs. 重伤 (grievous injury).** "丹田屏障碎裂" in a cultivation
  context is a `rank_up` (the barrier breaking = advancement), not damage — but "经脉尽断"
  is an injury. Use context.
- **关系翻转 (relationship flip).** "不再视她为妹妹" / "反目成仇" → terminate the old edge
  (`valid_to`) and create the new `hates`/`enemies_with` edge. Predicate stays ASCII.
- **赠予/归还 (gift/return) partial transactions.** "把钱留下，把令牌给我" → split into
  separate add/remove deltas, same as the English transaction test.

Use these as few-shot examples in the DB-01 prompt when `language` starts with `zh`.

---

## 6. 文风 (Prose voice)

- 都市/系统 lean fast, punchy, dialogue-heavy; 仙侠 leans more lyrical with 意境.
- Honour 视角 (POV) and 知识掩码 — a POV character narrates only what 他/她 perceives and
  knows (江湖 intrigue lives on information asymmetry).
- Keep the author's voice (run cognitive-alignment on any 文风 sample they provide and
  store it in `reference/` as a `style` resource).
