package org.rsmod.api.mechanics.status

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test
import org.rsmod.api.mechanics.status.PoisonGearBonus.Piece

class PoisonGearBonusTest {
    private val helm = Piece(damageDealt = 10, setPiece = true)
    private val chest = Piece(damageDealt = 0, setPiece = true)
    private val legs = Piece(damageDealt = 0, setPiece = true)
    private val ring = Piece(damageDealt = 5, setPiece = false, extraHits = 1)
    private val amulet = Piece(damageDealt = 5, setPiece = false, extraHits = 1)

    @Test
    fun `helm alone adds ten percent`() {
        assertEquals(10, PoisonGearBonus.total(listOf(helm)))
        assertEquals(0, PoisonGearBonus.damageDealtPercent(null))
    }

    @Test
    fun `two set pieces are not a full set`() {
        assertEquals(10, PoisonGearBonus.total(listOf(helm, chest)))
    }

    @Test
    fun `full set doubles set pieces only`() {
        assertEquals(20, PoisonGearBonus.total(listOf(helm, chest, legs)))
        assertEquals(25, PoisonGearBonus.total(listOf(helm, chest, legs, ring)))
        assertEquals(2, PoisonGearBonus.multiplier(3))
        assertEquals(1, PoisonGearBonus.multiplier(2))
    }

    @Test
    fun `ring and amulet each add an extra splat`() {
        assertEquals(0, PoisonGearBonus.totalExtraHits(listOf(helm, chest, legs)))
        assertEquals(1, PoisonGearBonus.totalExtraHits(listOf(helm, ring)))
        assertEquals(2, PoisonGearBonus.totalExtraHits(listOf(helm, chest, legs, ring, amulet)))
        assertEquals(0, PoisonGearBonus.extraHits(null))
    }
}
