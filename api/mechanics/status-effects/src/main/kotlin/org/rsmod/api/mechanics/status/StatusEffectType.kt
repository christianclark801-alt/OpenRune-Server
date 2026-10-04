package org.rsmod.api.mechanics.status

/** A stat a status effect changes. Every modifier is additive across active effects. */
public enum class StatusStat {
    PoisonHitsPerTick,
    PoisonDamageTakenPercent,
    VenomDamageTakenPercent,
}

/**
 * One kind of status effect. Its [varn] holds the map clock it expires on, so re-applying it
 * refreshes the duration instead of stacking; different effects add together.
 */
public class StatusEffectType(public val varn: String, public val modifiers: Map<StatusStat, Int>) {
    public fun modifier(stat: StatusStat): Int = modifiers[stat] ?: 0
}

public object StatusEffectTypes {
    public val toxic_mark: StatusEffectType =
        StatusEffectType("varn.status_toxic_mark", mapOf(StatusStat.PoisonHitsPerTick to 1))

    public val toxic_shroud: StatusEffectType =
        StatusEffectType("varn.status_toxic_shroud", mapOf(StatusStat.PoisonHitsPerTick to 1))

    public val poison_weakness: StatusEffectType =
        StatusEffectType(
            "varn.status_poison_weakness",
            mapOf(StatusStat.PoisonDamageTakenPercent to 50),
        )

    public val all: List<StatusEffectType> = listOf(toxic_mark, toxic_shroud, poison_weakness)

    public fun byName(name: String): StatusEffectType? =
        all.firstOrNull { it.varn == "varn.status_$name" }
}
