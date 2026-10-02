package org.rsmod.content.other.bossatlas

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertInstanceOf
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class BossAtlasLogicTest {
    @Test
    fun `boss ids fit in the six bit favourite varbits`() {
        assertTrue(Boss.entries.size <= Boss.MAX_ID + 1)
        assertTrue(encodeFavourite(Boss.entries.last()) <= 63)
    }

    @Test
    fun `boss keys are unique so per boss varps never collide`() {
        assertEquals(Boss.entries.size, Boss.entries.map { it.key }.toSet().size)
    }

    @Test
    fun `every npc maps to exactly one boss`() {
        val npcs = Boss.entries.flatMap { it.npcs }
        assertEquals(npcs.size, npcs.toSet().size)
        for (boss in Boss.entries) {
            for (npc in boss.npcs) {
                assertEquals(boss, Boss.forNpc(npc))
            }
        }
    }

    @Test
    fun `favourite encoding round trips and zero means empty`() {
        assertNull(decodeFavourite(0))
        for (boss in Boss.entries) {
            assertEquals(boss, decodeFavourite(encodeFavourite(boss)))
        }
    }

    @Test
    fun `a sixth favourite is rejected and unstarring frees a slot`() {
        var favourites = emptyList<Boss>()
        for (boss in Boss.entries.take(MAX_FAVOURITES)) {
            val result = toggledFavourites(favourites, boss)
            assertInstanceOf(FavouriteToggle.Added::class.java, result)
            favourites = result.favourites
        }
        val full = toggledFavourites(favourites, Boss.Nex)
        assertInstanceOf(FavouriteToggle.Full::class.java, full)
        assertEquals(favourites, full.favourites)

        val removed = toggledFavourites(favourites, favourites.first())
        assertInstanceOf(FavouriteToggle.Removed::class.java, removed)
        assertEquals(MAX_FAVOURITES - 1, removed.favourites.size)
    }

    @Test
    fun `favourites are listed first in every tab`() {
        val favourites = listOf(Boss.Callisto, Boss.Vorkath)
        val all = bossesFor(TAB_ALL, "", favourites)
        assertEquals(favourites, all.take(2))
        assertEquals(Boss.entries.size, all.size)

        val hard = bossesFor(tabOf(BossCategory.Hard), "", favourites)
        assertEquals(Boss.Vorkath, hard.first())
        assertTrue(hard.all { it.category == BossCategory.Hard })
    }

    @Test
    fun `favourites tab lists only starred bosses in star order`() {
        val favourites = listOf(Boss.Zulrah, Boss.KingBlackDragon)
        assertEquals(favourites, bossesFor(TAB_FAVOURITES, "", favourites))
    }

    @Test
    fun `search matches names and categories across every tab`() {
        val results = bossesFor(TAB_FAVOURITES, "  hydra ", emptyList())
        assertEquals(listOf(Boss.AlchemicalHydra), results)

        val wildy = bossesFor(TAB_ALL, "wilderness", emptyList())
        assertEquals(Boss.entries.filter { it.category == BossCategory.Wilderness }, wildy)
    }

    @Test
    fun `cooldown rounds up to whole seconds`() {
        assertEquals(11, cooldownSecondsLeft(deadline = 117, mapClock = 100))
        assertEquals(10, cooldownSecondsLeft(deadline = 116, mapClock = 100))
        assertEquals(1, cooldownSecondsLeft(deadline = 101, mapClock = 100))
        assertEquals(0, cooldownSecondsLeft(deadline = 100, mapClock = 100))
    }

    @Test
    fun `kill times and gp values are formatted for display`() {
        assertEquals("-", formatKillTime(0))
        assertEquals("1:30.0", formatKillTime(150))
        assertEquals("0:00.6", formatKillTime(1))
        assertEquals("950", formatGp(950))
        assertEquals("250K", formatGp(250_000))
        assertEquals("12.5M", formatGp(12_500_000))
    }

    private fun tabOf(category: BossCategory): Int = category.ordinal + 2
}
