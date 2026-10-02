package org.rsmod.api.npc.hit.modifier

import org.rsmod.game.entity.Npc
import org.rsmod.game.entity.Player
import org.rsmod.game.hit.HitBuilder

public fun interface PlayerNpcDamageModifier {
    public fun modify(hit: HitBuilder, target: Npc, source: Player)
}
