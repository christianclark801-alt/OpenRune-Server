package org.rsmod.api.mechanics.status

import org.rsmod.api.config.refs.params
import org.rsmod.game.entity.Npc
import org.rsmod.game.entity.Player

public object NpcStatusEffects {
    public const val PERMANENT: Int = Int.MAX_VALUE

    private const val INACTIVE = 0

    public fun apply(npc: Npc, type: StatusEffectType, ticks: Int) {
        npc.vars[type.varn] = expiry(npc.currentMapClock, ticks)
    }

    public fun remove(npc: Npc, type: StatusEffectType) {
        npc.vars[type.varn] = INACTIVE
    }

    public fun isActive(npc: Npc, type: StatusEffectType): Boolean =
        isActive(npc.vars[type.varn], npc.currentMapClock)

    public fun total(npc: Npc, stat: StatusStat): Int =
        total(stat, npc.currentMapClock, StatusEffectTypes.all, innate(npc, stat)) {
            npc.vars[it.varn]
        }

    public fun poisonHits(npc: Npc): Int = 1 + total(npc, StatusStat.PoisonHitsPerTick)

    public fun poisonDamage(npc: Npc, base: Int, source: Player? = null): Int =
        scale(
            base,
            total(npc, StatusStat.PoisonDamageTakenPercent) +
                PoisonGearBonus.damageDealtPercent(source),
        )

    public fun venomDamage(npc: Npc, base: Int, source: Player? = null): Int =
        scale(
            base,
            total(npc, StatusStat.VenomDamageTakenPercent) +
                PoisonGearBonus.damageDealtPercent(source),
        )

    private fun innate(npc: Npc, stat: StatusStat): Int =
        when (stat) {
            StatusStat.PoisonDamageTakenPercent ->
                npc.visType.paramOrNull(params.npc_poison_damage_taken) ?: 0
            else -> 0
        }

    internal fun expiry(clock: Int, ticks: Int): Int =
        if (ticks == PERMANENT) PERMANENT else clock + ticks

    internal fun isActive(expiry: Int, clock: Int): Boolean = expiry != INACTIVE && expiry > clock

    internal fun total(
        stat: StatusStat,
        clock: Int,
        types: List<StatusEffectType>,
        innate: Int,
        expiryOf: (StatusEffectType) -> Int,
    ): Int =
        innate +
            types.sumOf { type ->
                if (isActive(expiryOf(type), clock)) type.modifier(stat) else 0
            }

    internal fun scale(base: Int, percent: Int): Int = base * (100 + percent) / 100
}
