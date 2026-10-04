package org.rsmod.content.other.soulforge

import dev.openrune.types.ItemServerType
import org.rsmod.game.inv.InvObj

/** An item the forge upgrades through fixed tiers of effects instead of +strength levels. */
interface SpecialForge {
    val maxTier: Int
    val cost: Int
    val chance: Int

    fun matches(type: ItemServerType): Boolean

    fun describe(tier: Int): String

    fun tier(obj: InvObj?): Int = obj?.let { SoulForgeLevels.level(it.vars) } ?: 0
}

internal object SpecialForges {
    private val all = listOf(HolyWaterForge, PoisonBladesForge)

    fun of(type: ItemServerType): SpecialForge? = all.firstOrNull { it.matches(type) }
}
