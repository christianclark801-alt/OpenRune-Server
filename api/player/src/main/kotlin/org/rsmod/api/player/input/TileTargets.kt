package org.rsmod.api.player.input

import jakarta.inject.Singleton
import java.util.WeakHashMap
import org.rsmod.game.entity.Player
import org.rsmod.map.CoordGrid

/**
 * Lets a script take a player's next map click as a tile pick: while a request is pending, a walk
 * or minimap click is handed to it instead of moving the player.
 */
@Singleton
public class TileTargets {
    private val pending = WeakHashMap<Player, (CoordGrid) -> Unit>()

    public fun request(player: Player, onTile: (CoordGrid) -> Unit) {
        pending[player] = onTile
    }

    public fun cancel(player: Player): Boolean = pending.remove(player) != null

    public fun isTargeting(player: Player): Boolean = player in pending

    public fun consume(player: Player, coords: CoordGrid): Boolean {
        val onTile = pending.remove(player) ?: return false
        onTile(coords)
        return true
    }
}
