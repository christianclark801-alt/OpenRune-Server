package org.rsmod.api.droptable

import dtx.impl.chance.RateBoosts
import org.rsmod.game.entity.Npc
import org.rsmod.game.entity.Player

public object DropRateModifiers {
    @Volatile public var serverMultiplier: Double = 1.0

    @Volatile public var playerMultiplier: (Player) -> Double = { 1.0 }

    @Volatile public var killMultiplier: (Player, Npc) -> Double = { _, _ -> 1.0 }

    public fun multiplierFor(player: Player): Double = serverMultiplier * playerMultiplier(player)

    public fun install() {
        RateBoosts.multiplier = { target, _ ->
            if (target is Player) multiplierFor(target) else serverMultiplier
        }
        RateBoosts.rareMultiplier = { target, args ->
            val npc = args[KillRollContext.npc]
            if (target is Player && npc != null) killMultiplier(target, npc) else 1.0
        }
    }
}
