package org.rsmod.api.death

import org.rsmod.game.entity.Npc
import org.rsmod.game.entity.Player

/**
 * Notified for every drop-table item awarded to [Player] from killing [Npc], including drops that
 * a [NpcDeathDropHook] consumed instead of spawning on the floor.
 */
public fun interface NpcLootListener {
    public fun onLoot(player: Player, npc: Npc, obj: String, count: Int)
}
