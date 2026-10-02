package org.rsmod.content.other.bossatlas

import jakarta.inject.Inject
import jakarta.inject.Singleton
import org.rsmod.api.player.vars.VarPlayerIntMapSetter
import org.rsmod.game.entity.Player

/**
 * Fired after every tracked boss kill. Bind an implementation with
 * `addSetBinding<BossKillListener>(...)` in a `PluginModule` (e.g. a perk unlock system) and read
 * the current numbers from [BossStats].
 */
fun interface BossKillListener {
    fun onBossKill(player: Player, boss: Boss)
}

@Singleton
class BossStats @Inject constructor(private val killListeners: Set<BossKillListener>) {
    fun hasKillCount(boss: Boss): Boolean = boss.kills.isNotEmpty()

    fun killCount(player: Player, boss: Boss): Int = boss.kills.sumOf { player.vars[it.varp] }

    fun personalBestTicks(player: Player, boss: Boss): Int = player.vars[boss.pbVarp]

    fun lootValue(player: Player, boss: Boss): Long = player.vars[boss.lootVarp].toLong()

    fun recordKillTime(player: Player, boss: Boss, ticks: Int): Boolean {
        val best = personalBestTicks(player, boss)
        if (ticks <= 0 || (best in 1..ticks)) {
            return false
        }
        VarPlayerIntMapSetter.set(player, boss.pbVarp, ticks)
        return true
    }

    fun addLoot(player: Player, boss: Boss, value: Long) {
        if (value <= 0) {
            return
        }
        val total = (lootValue(player, boss) + value).coerceAtMost(Int.MAX_VALUE.toLong())
        VarPlayerIntMapSetter.set(player, boss.lootVarp, total.toInt())
    }

    internal fun notifyKill(player: Player, boss: Boss) {
        for (listener in killListeners) {
            listener.onBossKill(player, boss)
        }
    }
}
