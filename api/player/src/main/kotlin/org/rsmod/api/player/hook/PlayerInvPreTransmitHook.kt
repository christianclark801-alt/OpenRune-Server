package org.rsmod.api.player.hook

import org.rsmod.game.entity.Player

/**
 * Called once per player during post-tick processing, before modified inventories are
 * transmitted. Changes made here to an already-transmitted inventory go out in the same tick's
 * packets as the changes that triggered them.
 */
public fun interface PlayerInvPreTransmitHook {
    public fun beforeInvTransmit(player: Player)
}
