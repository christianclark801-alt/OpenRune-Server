package org.rsmod.api.player.gamemode

import org.rsmod.api.player.ironman.isAnyIronman
import org.rsmod.api.player.vars.intVarBit
import org.rsmod.game.entity.Player

public enum class XpMode(
    public val id: Int,
    public val label: String,
    public val xpRate: Double,
    public val bossDropRate: Double,
) {
    Easy(id = 1, label = "Easy", xpRate = 25.0, bossDropRate = 1.5),
    Medium(id = 2, label = "Medium", xpRate = 10.0, bossDropRate = 2.5),
    Hard(id = 3, label = "Hard", xpRate = 3.0, bossDropRate = 4.0);

    public companion object {
        public const val IRONMAN_DROP_BONUS: Double = 0.5

        public fun fromId(id: Int): XpMode? = entries.firstOrNull { it.id == id }
    }
}

public var Player.xpModeId: Int by intVarBit("varbit.xp_mode")

public val Player.xpMode: XpMode?
    get() = XpMode.fromId(xpModeId)

public fun bossDropMultiplier(mode: XpMode, ironman: Boolean): Double =
    mode.bossDropRate + if (ironman) XpMode.IRONMAN_DROP_BONUS else 0.0

public val Player.bossDropMultiplier: Double
    get() = xpMode?.let { bossDropMultiplier(it, isAnyIronman) } ?: 1.0
