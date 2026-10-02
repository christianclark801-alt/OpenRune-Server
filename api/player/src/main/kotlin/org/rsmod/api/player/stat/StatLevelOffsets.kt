package org.rsmod.api.player.stat

import org.rsmod.game.entity.Player

public object StatLevelOffsets {
    @Volatile public var offset: (Player, String) -> Int = { _, _ -> 0 }
}

/**
 * Returns the level that [stat] restores, regenerates and boosts from: the [statBase] level plus
 * any permanent [StatLevelOffsets] bonus.
 */
public fun Player.statEffectiveBase(stat: String): Int =
    (statBase(stat) + StatLevelOffsets.offset(this, stat)).coerceIn(0, 255)
