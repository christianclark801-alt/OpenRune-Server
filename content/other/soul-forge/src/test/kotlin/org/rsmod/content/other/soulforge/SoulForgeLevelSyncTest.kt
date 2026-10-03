package org.rsmod.content.other.soulforge

import dev.openrune.types.util.UncheckedType
import org.junit.jupiter.api.Assertions.assertArrayEquals
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.rsmod.game.inv.InvObj

@OptIn(UncheckedType::class)
class SoulForgeLevelSyncTest {
    @Test
    fun `entries carry the real obj with level as count and skip unforged or empty slots`() {
        val objs = arrayOfNulls<InvObj>(5)
        objs[1] = InvObj(4716, 1, vars = SoulForgeLevels.withLevel(0, 3))
        objs[2] = InvObj(4720, 1)
        objs[4] = InvObj(4722, 1, vars = SoulForgeLevels.withLevel(1234, SoulForgeLevels.maxLevel))

        val expected =
            arrayOf(null, InvObj(4716, 3), null, null, InvObj(4722, SoulForgeLevels.maxLevel))
        assertArrayEquals(expected, levelEntriesOf(objs))
    }

    @Test
    fun `moving a forged obj moves its entry with it`() {
        val before = arrayOfNulls<InvObj>(3)
        before[0] = InvObj(4716, 1, vars = SoulForgeLevels.withLevel(0, 2))
        val after = arrayOfNulls<InvObj>(3)
        after[2] = before[0]
        after[0] = InvObj(4720, 1)

        val entries = levelEntriesOf(after)
        assertEquals(null, entries[0])
        assertEquals(InvObj(4716, 2), entries[2])
    }

    @Test
    fun `bank sized mirrors keep forged entries at their exact slot`() {
        val bank = arrayOfNulls<InvObj>(1410)
        bank[0] = InvObj(4716, 1)
        bank[1409] = InvObj(4722, 1, vars = SoulForgeLevels.withLevel(0, 4))

        val entries = levelEntriesOf(bank)
        assertEquals(1410, entries.size)
        assertEquals(InvObj(4722, 4), entries[1409])
        assertEquals(1, entries.count { it != null })
    }

    @Test
    fun `levels inventory fits inventory and worn slots`() {
        assertEquals(28, WORN_LEVEL_OFFSET)
        assertTrue(SoulForgeLevels.maxLevel >= 1)
    }
}
