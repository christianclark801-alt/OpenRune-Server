package org.rsmod.api.mechanics.status

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class NpcStatusEffectsTest {
    private val types = StatusEffectTypes.all

    @Test
    fun `effects expire on their clock`() {
        val expiry = NpcStatusEffects.expiry(clock = 100, ticks = 30)
        assertTrue(NpcStatusEffects.isActive(expiry, clock = 129))
        assertFalse(NpcStatusEffects.isActive(expiry, clock = 130))
        assertFalse(NpcStatusEffects.isActive(0, clock = 0))
        val permanent = NpcStatusEffects.expiry(clock = 100, ticks = NpcStatusEffects.PERMANENT)
        assertTrue(NpcStatusEffects.isActive(permanent, clock = 1_000_000))
    }

    @Test
    fun `poison hits rise with each distinct effect`() {
        fun hits(vararg active: StatusEffectType): Int =
            1 + NpcStatusEffects.total(StatusStat.PoisonHitsPerTick, 10, types, innate = 0) {
                if (it in active) 50 else 0
            }
        assertEquals(1, hits())
        assertEquals(2, hits(StatusEffectTypes.toxic_mark))
        assertEquals(3, hits(StatusEffectTypes.toxic_mark, StatusEffectTypes.toxic_shroud))
    }

    @Test
    fun `poison weakness and innate weakness add to damage taken`() {
        val applied =
            NpcStatusEffects.total(StatusStat.PoisonDamageTakenPercent, 10, types, innate = 0) {
                if (it == StatusEffectTypes.poison_weakness) 50 else 0
            }
        assertEquals(50, applied)
        assertEquals(6, NpcStatusEffects.scale(4, applied))
        val both =
            NpcStatusEffects.total(StatusStat.PoisonDamageTakenPercent, 10, types, innate = 50) {
                if (it == StatusEffectTypes.poison_weakness) 50 else 0
            }
        assertEquals(8, NpcStatusEffects.scale(4, both))
        assertEquals(40, NpcStatusEffects.scale(40, 0))
    }

    @Test
    fun `effects are looked up by short name`() {
        assertEquals(StatusEffectTypes.poison_weakness, StatusEffectTypes.byName("poison_weakness"))
        assertEquals(null, StatusEffectTypes.byName("nope"))
    }
}
