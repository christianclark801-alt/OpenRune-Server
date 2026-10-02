package org.rsmod.content.other.soulforge

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class SoulDicePerksTest {
    @Test
    fun `first roll is free and later rolls cost essence`() {
        val fresh = SoulDiceState(0)
        assertTrue(fresh.freeRollAvailable)
        assertEquals(0, fresh.rollCost)
        val used = fresh.withRollUsed()
        assertFalse(used.freeRollAvailable)
        assertEquals(SoulDiceState.ROLL_COST, used.rollCost)
    }

    @Test
    fun `roll pool never contains an owned perk`() {
        var state = SoulDiceState(0)
        val rolled = mutableListOf<SoulPerk>()
        while (state.rollPool.isNotEmpty()) {
            val pick = state.rollPool.last()
            assertFalse(state.has(pick))
            rolled += pick
            state = state.withRollUsed().withLevel(pick, 1)
        }
        assertEquals(SoulPerk.starters.toSet(), rolled.toSet())
        assertEquals(SoulPerk.starters.size, rolled.size)
        assertTrue(state.starterComplete)
    }

    @Test
    fun `boss slayer unlocks only after every starter perk`() {
        var state = SoulDiceState(0)
        for (perk in SoulPerk.starters) {
            assertFalse(state.rowUnlocked(SoulRow.BossSlayer))
            state = state.withLevel(perk, 1)
        }
        assertTrue(state.rowUnlocked(SoulRow.BossSlayer))
    }

    @Test
    fun `true haste unlocks at half of the boss slayer levels`() {
        assertEquals(5, SoulDiceState.TRUE_HASTE_REQUIREMENT)
        var state = SoulDiceState(0)
        for (perk in SoulPerk.starters) {
            state = state.withLevel(perk, 1)
        }
        state = state.withLevel(SoulPerk.BossDamage, 3).withLevel(SoulPerk.DemonDamage, 1)
        assertFalse(state.rowUnlocked(SoulRow.TrueHaste))
        state = state.withLevel(SoulPerk.DemonDamage, 2)
        assertTrue(state.rowUnlocked(SoulRow.TrueHaste))
    }

    @Test
    fun `levels stack and stay within their own bits`() {
        var state = SoulDiceState(0).withRollUsed()
        for (perk in SoulPerk.entries) {
            state = state.withLevel(perk, perk.maxLevel)
        }
        for (perk in SoulPerk.entries) {
            assertEquals(perk.maxLevel, state.level(perk))
        }
        assertEquals(30, state.percent(SoulPerk.BossDamage))
        assertEquals(45, state.percent(SoulPerk.DemonDamage))
        assertEquals(30, state.percent(SoulPerk.RaidDamage))
        assertFalse(state.freeRollAvailable)

        val cleared = state.withLevel(SoulPerk.DemonDamage, 0)
        assertEquals(0, cleared.level(SoulPerk.DemonDamage))
        assertEquals(3, cleared.level(SoulPerk.BossDamage))
        assertEquals(3, cleared.level(SoulPerk.RaidDamage))
    }

    @Test
    fun `true haste shares the starter two tick flags`() {
        val state = SoulDiceState(0).withLevel(SoulPerk.TwoTickRange, 1)
        assertTrue(state.has(SoulPerk.HasteRange))
        assertFalse(state.has(SoulPerk.HasteMelee))
        assertTrue(SoulDiceState(0).withLevel(SoulPerk.HasteMagic, 1).has(SoulPerk.TwoTickMagic))
    }
}
