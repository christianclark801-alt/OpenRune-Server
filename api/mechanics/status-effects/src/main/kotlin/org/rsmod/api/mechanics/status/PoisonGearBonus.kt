package org.rsmod.api.mechanics.status

import org.rsmod.api.config.refs.params
import org.rsmod.game.entity.Player
import org.rsmod.game.type.getInvObj

/**
 * Poison gear a player wears: `param.poison_damage_dealt` adds that % to every poison and venom
 * hit they deal, pieces marked `param.poison_armour_set` double their effects once the full set
 * is worn, and `param.poison_extra_hits` adds that many extra splats to every poison and venom
 * hit.
 */
public object PoisonGearBonus {
    public const val FULL_SET: Int = 3
    public const val SET_MULTIPLIER: Int = 2

    internal data class Piece(val damageDealt: Int, val setPiece: Boolean, val extraHits: Int = 0)

    public fun setMultiplier(player: Player): Int = multiplier(pieces(player).count { it.setPiece })

    public fun damageDealtPercent(player: Player?): Int {
        if (player == null) {
            return 0
        }
        return total(pieces(player))
    }

    public fun extraHits(player: Player?): Int {
        if (player == null) {
            return 0
        }
        return totalExtraHits(pieces(player))
    }

    private fun pieces(player: Player): List<Piece> =
        player.worn.mapNotNull { obj ->
            obj ?: return@mapNotNull null
            val type = getInvObj(obj)
            Piece(
                damageDealt = type.paramOrNull(params.poison_damage_dealt) ?: 0,
                setPiece = (type.paramOrNull(params.poison_armour_set) ?: 0) > 0,
                extraHits = type.paramOrNull(params.poison_extra_hits) ?: 0,
            )
        }

    internal fun multiplier(setPieces: Int): Int = if (setPieces >= FULL_SET) SET_MULTIPLIER else 1

    internal fun total(pieces: List<Piece>): Int {
        val multiplier = multiplier(pieces.count { it.setPiece })
        return pieces.sumOf { if (it.setPiece) it.damageDealt * multiplier else it.damageDealt }
    }

    internal fun totalExtraHits(pieces: List<Piece>): Int = pieces.sumOf { it.extraHits }
}
