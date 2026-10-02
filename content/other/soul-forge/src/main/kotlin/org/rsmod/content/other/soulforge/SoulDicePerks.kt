package org.rsmod.content.other.soulforge

internal enum class SoulRow(val label: String) {
    Starter("Starter Perks"),
    BossSlayer("Boss Slayer Perks"),
    TrueHaste("True Haste Perks"),
}

internal enum class SoulPerk(
    val row: SoulRow,
    val label: String,
    val description: String,
    val cost: Int,
    val maxLevel: Int,
    val percentPerLevel: Int,
    private val shift: Int,
    private val mask: Int,
) {
    TwoTickMelee(SoulRow.Starter, "2-tick Melee", "Melee every 2 ticks", 0, 1, 0, 1, 0x1),
    TwoTickRange(SoulRow.Starter, "2-tick Range", "Ranged every 2 ticks", 0, 1, 0, 2, 0x1),
    TwoTickMagic(SoulRow.Starter, "2-tick Magic", "Magic every 2 ticks", 0, 1, 0, 3, 0x1),
    Lifesteal(SoulRow.Starter, "10% Lifesteal", "Heal 10% of damage", 0, 1, 10, 4, 0x1),
    CombatStats(SoulRow.Starter, "+20 Stats", "+20 combat levels", 0, 1, 0, 5, 0x1),
    BossDamage(SoulRow.BossSlayer, "Boss Damage", "+10% vs bosses per level", 50, 3, 10, 6, 0x3),
    DemonDamage(SoulRow.BossSlayer, "Demon Damage", "+15% vs demons per level", 50, 3, 15, 8, 0x3),
    RaidDamage(SoulRow.BossSlayer, "Raid Damage", "+10% in raids per level", 50, 3, 10, 10, 0x3),
    HasteMelee(SoulRow.TrueHaste, "Melee Haste", "Permanent 2-tick melee", 100, 1, 0, 1, 0x1),
    HasteRange(SoulRow.TrueHaste, "Range Haste", "Permanent 2-tick ranged", 100, 1, 0, 2, 0x1),
    HasteMagic(SoulRow.TrueHaste, "Magic Haste", "Permanent 2-tick magic", 100, 1, 0, 3, 0x1);

    fun level(packed: Int): Int = (packed ushr shift) and mask

    fun withLevel(packed: Int, level: Int): Int =
        (packed and (mask shl shift).inv()) or ((level.coerceIn(0, maxLevel) and mask) shl shift)

    companion object {
        val starters: List<SoulPerk> = entries.filter { it.row == SoulRow.Starter }
        val bossSlayer: List<SoulPerk> = entries.filter { it.row == SoulRow.BossSlayer }
    }
}

@JvmInline
internal value class SoulDiceState(val packed: Int) {
    val freeRollAvailable: Boolean
        get() = packed and FREE_ROLL_USED == 0

    val rollCost: Int
        get() = if (freeRollAvailable) 0 else ROLL_COST

    val rollPool: List<SoulPerk>
        get() = SoulPerk.starters.filter { !has(it) }

    val starterComplete: Boolean
        get() = rollPool.isEmpty()

    val bossSlayerLevels: Int
        get() = SoulPerk.bossSlayer.sumOf { level(it) }

    fun level(perk: SoulPerk): Int = perk.level(packed)

    fun has(perk: SoulPerk): Boolean = level(perk) > 0

    fun isMaxed(perk: SoulPerk): Boolean = level(perk) >= perk.maxLevel

    fun percent(perk: SoulPerk): Int = level(perk) * perk.percentPerLevel

    fun rowUnlocked(row: SoulRow): Boolean =
        when (row) {
            SoulRow.Starter -> true
            SoulRow.BossSlayer -> starterComplete
            SoulRow.TrueHaste -> starterComplete && bossSlayerLevels >= TRUE_HASTE_REQUIREMENT
        }

    fun withRollUsed(): SoulDiceState = SoulDiceState(packed or FREE_ROLL_USED)

    fun withLevel(perk: SoulPerk, level: Int): SoulDiceState =
        SoulDiceState(perk.withLevel(packed, level))

    companion object {
        const val ROLL_COST: Int = 100
        const val STAT_BONUS: Int = 20
        const val TWO_TICK_RATE: Int = 2

        private const val FREE_ROLL_USED = 0x1

        val TRUE_HASTE_REQUIREMENT: Int =
            (SoulPerk.bossSlayer.sumOf { it.maxLevel } + 1) / 2
    }
}
