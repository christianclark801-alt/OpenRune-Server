package org.rsmod.content.other.bossatlas

import java.util.Locale

const val MAX_FAVOURITES: Int = 5

const val TAB_FAVOURITES: Int = 0
const val TAB_ALL: Int = 1
const val TAB_COUNT: Int = 8

private val TAB_CATEGORIES: Map<Int, BossCategory> =
    BossCategory.entries.withIndex().associate { (index, category) -> index + 2 to category }

fun bossesFor(tab: Int, query: String, favourites: List<Boss>): List<Boss> {
    val trimmed = query.trim()
    val bosses =
        when {
            trimmed.isNotEmpty() -> Boss.entries.filter { it.matches(trimmed) }
            tab == TAB_FAVOURITES -> return favourites
            tab == TAB_ALL -> Boss.entries
            else -> {
                val category = TAB_CATEGORIES[tab] ?: return Boss.entries
                Boss.entries.filter { it.category == category }
            }
        }
    return bosses.sortedWith(
        compareBy<Boss> { !it.implemented }
            .thenBy { favourites.indexOf(it).takeIf { index -> index >= 0 } ?: Int.MAX_VALUE }
            .thenBy { it.combatLevel <= 0 }
            .thenByDescending { it.combatLevel }
            .thenBy { it.displayName.lowercase() },
    )
}

sealed interface FavouriteToggle {
    val favourites: List<Boss>

    data class Added(override val favourites: List<Boss>) : FavouriteToggle

    data class Removed(override val favourites: List<Boss>) : FavouriteToggle

    data class Full(override val favourites: List<Boss>) : FavouriteToggle
}

fun toggledFavourites(favourites: List<Boss>, boss: Boss): FavouriteToggle =
    when {
        boss in favourites -> FavouriteToggle.Removed(favourites - boss)
        favourites.size >= MAX_FAVOURITES -> FavouriteToggle.Full(favourites)
        else -> FavouriteToggle.Added(favourites + boss)
    }

fun encodeFavourite(boss: Boss?): Int = if (boss == null) 0 else boss.id + 1

fun decodeFavourite(value: Int): Boss? = if (value <= 0) null else Boss.forId(value - 1)

fun cooldownSecondsLeft(deadline: Int, mapClock: Int): Int =
    if (deadline <= mapClock) 0 else ((deadline - mapClock) * 6 + 9) / 10

fun formatKillTime(ticks: Int): String {
    if (ticks <= 0) {
        return "-"
    }
    val totalTenths = ticks * 6
    val minutes = totalTenths / 600
    val seconds = (totalTenths % 600) / 10
    val tenths = totalTenths % 10
    return "$minutes:${seconds.toString().padStart(2, '0')}.$tenths"
}

fun formatGp(value: Long): String =
    when {
        value >= 1_000_000_000 -> "%.2fB".format(Locale.ENGLISH, value / 1_000_000_000.0)
        value >= 1_000_000 -> "%.1fM".format(Locale.ENGLISH, value / 1_000_000.0)
        value >= 100_000 -> "${value / 1_000}K"
        else -> "%,d".format(Locale.ENGLISH, value)
    }

fun levelLabel(boss: Boss): String =
    if (boss.combatLevel <= 0) "Raid" else "Level ${boss.combatLevel}"
