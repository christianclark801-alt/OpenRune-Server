package org.rsmod.content.other.soulforge

import dev.openrune.rscm.RSCM.asRSCM
import dev.openrune.rscm.RSCMType
import dev.openrune.types.ItemServerType

object PoisonBladesForge : SpecialForge {
    override val maxTier: Int = 2
    override val cost: Int = 1000
    override val chance: Int = 100

    const val POISON_TIER = 1
    const val VENOM_TIER = 2

    private const val POISON_BLADES = "obj.poison_blades"

    override fun matches(type: ItemServerType): Boolean =
        type.id == POISON_BLADES.asRSCM(RSCMType.OBJ)

    override fun describe(tier: Int): String =
        when (tier) {
            0 -> "No venom"
            POISON_TIER -> "30%: 40 poison now + 40 after 6s"
            else -> "10%: 50-300 venom after 6s"
        }
}
