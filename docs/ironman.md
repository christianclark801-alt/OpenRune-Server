# Ironman

Modes sync via `Player.gamemode` + `varbit.ironman`. Admin: `::gamemode normal|ironman|uim|hcim`.

## UIM bank

Gate with `IronmanRestrictions.blockUimBank(player)` or `ProtectedAccess.tryOpenBank()`.
`inv.bank` is tagged `uimBlocked = true` for the same rule via `blockUimInventory`.

Unnote still works (note on banker / bank booth).

For other storage: set `uimBlocked = true` on the inv in `inv.toml`, re-pack, then `blockUimInventory`.

## HCIM safe deaths

Unsafe death demotes to Ironman. Before a scripted safe death:

```kotlin
player.markNextDeathSafe()
```

## Enforced

- Trade, foreign loot, Accept Aid
- UIM: no bank / deposit box; death keeps 0 items
- HCIM: unsafe death demotes
- Ironman: no combat XP (and ironman-blocked hitmark) on NPCs already damaged by another player

## Game modes

New accounts are locked into a two-step selection (`content/other/game-mode`) before they can
play: account type (Normal, Ironman, Hardcore, Ultimate), then XP mode.

| XP mode | XP rate | Boss drop rate | Ironman |
|---------|---------|----------------|---------|
| Easy    | 25x     | 1.5x           | +0.5x   |
| Medium  | 10x     | 2.5x           | +0.5x   |
| Hard    | 3x      | 4x             | +0.5x   |

- The XP rate is stored in `Player.xpRate`, which already applies to every `statAdvance`. The
  account type goes through `setGamemode`.
- `varbit.game_mode_state` is permanent: 0 means a legacy account that is never prompted,
  1 means the selection is pending, 2 means it is done. `varbit.xp_mode` is also permanent and
  holds the XP mode (1–3).
- The step and the step-one choice live in temp varbits. Nothing permanent is written until the
  XP mode is confirmed, so a logout mid-way restarts at step one.
- `XpMode` / `Player.bossDropMultiplier` live in `api/player/.../gamemode/XpMode.kt`. The boss
  drop rule is described in `docs/drops.md` → Game-mode boss multiplier.
