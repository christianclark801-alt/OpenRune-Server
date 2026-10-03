package org.rsmod.content.other.donatorshop

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class DonatorBoxTest {
    @Test
    fun `box ids are unique and fit the selection varbit`() {
        assertEquals(DonatorBox.entries.size, DonatorBox.entries.map { it.id }.toSet().size)
        assertTrue(DonatorBox.entries.all { it.id + 1 <= 7 })
    }

    @Test
    fun `boxes cost between 1 and 20 points`() {
        assertTrue(DonatorBox.entries.all { it.price in 1..20 })
    }

    @Test
    fun `every box has a valid reward table that fits the interface`() {
        for (box in DonatorBox.entries) {
            assertTrue(box.rewards.isNotEmpty())
            assertTrue(box.rewards.size <= DonatorBox.MAX_REWARDS)
            assertTrue(box.rewards.all { it.weight > 0 && it.min in 1..it.max })
            assertEquals(box.rewards.size, box.rewards.map { it.obj }.toSet().size)
        }
    }

    @Test
    fun `every roll in range maps to a reward in proportion to its weight`() {
        for (box in DonatorBox.entries) {
            val hits = (0 until box.totalWeight).groupingBy { box.rewardAt(it) }.eachCount()
            for (reward in box.rewards) {
                assertEquals(reward.weight, hits[reward])
            }
            assertThrows(IllegalStateException::class.java) { box.rewardAt(box.totalWeight) }
        }
    }

    @Test
    fun `each box has at least one rare reward but coins are never rare`() {
        for (box in DonatorBox.entries) {
            assertTrue(box.rewards.any(box::isRare))
            assertTrue(box.rewards.filter { it.obj == "obj.coins" }.none(box::isRare))
        }
    }
}
