package org.rsmod.content.other.soulforge

import dev.openrune.rscm.RSCM.asRSCM
import dev.openrune.rscm.RSCMType
import dev.openrune.types.ItemServerType
import org.rsmod.game.inv.InvObj

object HolyWaterForge {
    const val MAX_TIER = 2
    const val COST = 1000
    const val CHANCE = 100

    private const val HOLY_WATER = "obj.holy_water"

    fun tier(obj: InvObj?): Int = obj?.let { SoulForgeLevels.level(it.vars) } ?: 0

    fun isHolyWater(type: ItemServerType): Boolean = type.id == HOLY_WATER.asRSCM(RSCMType.OBJ)

    fun describe(tier: Int): String =
        when (tier) {
            0 -> "Poison 4 x4"
            1 -> "Poison 8 x4"
            else -> "Venom 8 x4, +2 per hit"
        }
}
