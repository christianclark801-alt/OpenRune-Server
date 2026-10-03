package org.rsmod.content.other.soulforge

import dev.openrune.types.util.UncheckedType
import jakarta.inject.Inject
import java.util.Collections
import java.util.WeakHashMap
import org.rsmod.api.player.hook.PlayerInvPreTransmitHook
import org.rsmod.api.player.startInvTransmit
import org.rsmod.api.player.stopInvTransmit
import org.rsmod.game.entity.Player
import org.rsmod.game.inv.InvObj
import org.rsmod.game.inv.Inventory

private const val LEVELS_INV = "inv.soul_forge_levels"
private const val BANK_LEVELS_INV = "inv.soul_forge_bank_levels"
private const val BANK_INV = "inv.bank"
private const val BANK_INTERFACE = "interface.bankmain"

internal const val WORN_LEVEL_OFFSET = 28

/**
 * Mirrors the forge level of every inventory, worn and (while the bank is open) bank slot into
 * hidden inventories, which the overridden inventory/equipment/bank clientscripts read to colour
 * forged item names; the client never receives obj vars. Each entry holds the real obj (count =
 * level) so the client only trusts it while the slot still holds that obj, and it runs before
 * transmission so the entries ship in the same tick as the inventory change itself.
 */
class SoulForgeLevelSync @Inject constructor() : PlayerInvPreTransmitHook {
    private val bankMirrored: MutableSet<Player> = Collections.newSetFromMap(WeakHashMap())

    override fun beforeInvTransmit(player: Player) {
        syncCarried(player)
        syncBank(player)
    }

    private fun syncCarried(player: Player) {
        val created = LEVELS_INV !in player.invMap
        if (!created && !player.inv.hasModifiedSlots() && !player.worn.hasModifiedSlots()) {
            return
        }
        val levels = player.invMap.getOrPut(LEVELS_INV)
        mirror(levels, levelEntriesOf(player.inv.objs), offset = 0)
        mirror(levels, levelEntriesOf(player.worn.objs), offset = WORN_LEVEL_OFFSET)
        if (created) {
            player.startInvTransmit(levels)
        }
    }

    private fun syncBank(player: Player) {
        val open = player.ui.containsModal(BANK_INTERFACE)
        if (!open) {
            if (bankMirrored.remove(player)) {
                player.stopInvTransmit(player.invMap.getOrPut(BANK_LEVELS_INV))
            }
            return
        }
        val bank = player.invMap.getOrPut(BANK_INV)
        val opening = bankMirrored.add(player)
        if (!opening && !bank.hasModifiedSlots()) {
            return
        }
        val levels = player.invMap.getOrPut(BANK_LEVELS_INV)
        mirror(levels, levelEntriesOf(bank.objs), offset = 0)
        if (opening) {
            player.startInvTransmit(levels)
        }
    }

    private fun mirror(levels: Inventory, entries: Array<InvObj?>, offset: Int) {
        for (slot in entries.indices) {
            val target = offset + slot
            if (target >= levels.size) {
                return
            }
            if (levels[target] != entries[slot]) {
                levels[target] = entries[slot]
            }
        }
    }
}

@OptIn(UncheckedType::class)
internal fun levelEntriesOf(objs: Array<InvObj?>): Array<InvObj?> =
    Array(objs.size) { slot ->
        val obj = objs[slot] ?: return@Array null
        val level = SoulForgeLevels.level(obj.vars)
        if (level > 0) InvObj(obj.id, level) else null
    }
