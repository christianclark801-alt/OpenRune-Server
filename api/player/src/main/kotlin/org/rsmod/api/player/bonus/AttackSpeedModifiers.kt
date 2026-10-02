package org.rsmod.api.player.bonus

import org.rsmod.game.entity.Player

public enum class AttackSpeedStyle {
    Melee,
    Ranged,
    Magic,
}

public object AttackSpeedModifiers {
    @Volatile public var override: (Player, AttackSpeedStyle) -> Int? = { _, _ -> null }

    public fun apply(player: Player, style: AttackSpeedStyle, rate: Int): Int {
        val modified = override(player, style) ?: return rate
        return minOf(modified, rate)
    }
}
