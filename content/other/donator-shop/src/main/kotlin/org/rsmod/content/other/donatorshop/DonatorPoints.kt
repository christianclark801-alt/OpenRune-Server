package org.rsmod.content.other.donatorshop

import org.rsmod.api.player.vars.intVarp
import org.rsmod.game.entity.Player

var Player.donatorPoints by intVarp("varp.donator_points")
var Player.donatorPointsTotal by intVarp("varp.donator_points_total")

object DonatorPoints {
    fun add(player: Player, amount: Int) {
        if (amount <= 0) return
        player.donatorPoints = (player.donatorPoints.toLong() + amount).coerceAtMost(Int.MAX_VALUE.toLong()).toInt()
        player.donatorPointsTotal =
            (player.donatorPointsTotal.toLong() + amount).coerceAtMost(Int.MAX_VALUE.toLong()).toInt()
    }

    fun remove(player: Player, amount: Int): Int {
        val removed = amount.coerceIn(0, player.donatorPoints)
        player.donatorPoints -= removed
        return removed
    }

    fun spend(player: Player, amount: Int): Boolean {
        if (amount < 0 || player.donatorPoints < amount) return false
        player.donatorPoints -= amount
        return true
    }
}
