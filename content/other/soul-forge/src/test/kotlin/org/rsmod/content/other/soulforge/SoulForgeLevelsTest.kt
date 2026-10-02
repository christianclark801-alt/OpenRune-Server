package org.rsmod.content.other.soulforge

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Test

class SoulForgeLevelsTest {
    @Test
    fun `level round trips without touching other vars bits`() {
        val charges = 1234
        for (level in 0..SoulForgeLevels.maxLevel) {
            val vars = SoulForgeLevels.withLevel(charges, level)
            assertEquals(level, SoulForgeLevels.level(vars))
            assertEquals(charges, vars and 0xFFFFFF)
        }
    }

    @Test
    fun `costs rise and chances fall each level`() {
        val levels = SoulForgeLevels.all()
        assertEquals(5, levels.first().cost)
        assertEquals(50, levels.first().chancePercent)
        levels.zipWithNext().forEach { (a, b) ->
            assert(b.cost > a.cost)
            assert(b.chancePercent < a.chancePercent)
        }
        assertNull(SoulForgeLevels.next(SoulForgeLevels.maxLevel))
    }

    @Test
    fun `style follows the highest attack bonus`() {
        assertEquals(ForgeStyle.Melee, SoulForgeLevels.styleOf(melee = 0, ranged = 0, magic = 0))
        assertEquals(ForgeStyle.Melee, SoulForgeLevels.styleOf(melee = 82, ranged = 0, magic = 0))
        assertEquals(ForgeStyle.Ranged, SoulForgeLevels.styleOf(melee = 0, ranged = 30, magic = -1))
        assertEquals(ForgeStyle.Magic, SoulForgeLevels.styleOf(melee = 0, ranged = -5, magic = 20))
    }

    @Test
    fun `bonus is two per level in the item's style`() {
        assertNull(SoulForgeLevels.bonusFor(ForgeStyle.Melee, 0))
        assertEquals(2, SoulForgeLevels.bonusFor(ForgeStyle.Melee, 1)?.meleeStr)
        assertEquals(6, SoulForgeLevels.bonusFor(ForgeStyle.Ranged, 3)?.rangedStr)
        assertEquals(40, SoulForgeLevels.bonusFor(ForgeStyle.Magic, 2)?.magicDmg)
    }
}
