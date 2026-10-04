package org.rsmod.content.other.soulforge

import dev.openrune.types.util.UncheckedType
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test
import org.rsmod.game.inv.InvObj

@OptIn(UncheckedType::class)
class PoisonBladesForgeTest {
    @Test
    fun `tier reads the forge level stored in the blades' vars`() {
        assertEquals(0, PoisonBladesForge.tier(null))
        for (tier in 0..PoisonBladesForge.maxTier) {
            val obj = InvObj(id = 1, count = 1, vars = SoulForgeLevels.withLevel(0, tier))
            assertEquals(tier, PoisonBladesForge.tier(obj))
        }
    }

    @Test
    fun `tiers describe poison then venom`() {
        assertEquals(2, PoisonBladesForge.maxTier)
        assertEquals(1000, PoisonBladesForge.cost)
        assertEquals(100, PoisonBladesForge.chance)
        assertEquals("30%: 40 poison now + 40 after 6s", PoisonBladesForge.describe(1))
        assertEquals("10%: 50-300 venom after 6s", PoisonBladesForge.describe(2))
    }
}
