package org.rsmod.content.other.soulforge

import dev.openrune.rscm.RSCM.asRSCM
import dev.openrune.rscm.RSCMType
import dev.openrune.types.ItemServerType

object HolyWaterForge : SpecialForge {
    override val maxTier: Int = 2
    override val cost: Int = 1000
    override val chance: Int = 100

    private const val HOLY_WATER = "obj.holy_water"

    fun isHolyWater(type: ItemServerType): Boolean = type.id == HOLY_WATER.asRSCM(RSCMType.OBJ)

    override fun matches(type: ItemServerType): Boolean = isHolyWater(type)

    override fun describe(tier: Int): String =
        when (tier) {
            0 -> "Poison 4 x4"
            1 -> "Poison 8 x4"
            else -> "Venom 8 x4, +2 per hit"
        }
}
