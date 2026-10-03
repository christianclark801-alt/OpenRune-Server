package org.rsmod.api.npc.hit

import org.rsmod.game.entity.Npc
import org.rsmod.game.entity.Player
import org.rsmod.game.hit.Hit

public fun interface NpcDamageContributor {
    public fun onPlayerDamageNpc(npc: Npc, source: Player, damage: Int)

    public fun onPlayerHitNpc(npc: Npc, source: Player, hit: Hit) {
        onPlayerDamageNpc(npc, source, hit.damage)
    }
}
