package org.rsmod.content.other.consumables.potion

import org.rsmod.api.config.Constants
import org.rsmod.api.player.events.interact.HeldUEvents
import org.rsmod.api.player.protect.ProtectedAccess
import org.rsmod.api.script.onOpHeldU
import org.rsmod.api.table.PotionRow
import org.rsmod.plugin.scripts.PluginScript
import org.rsmod.plugin.scripts.ScriptContext

class PotionDecantScript : PluginScript() {
    override fun ScriptContext.startup() {
        PotionRow.all()
            .filter { !it.mix && it.items.size > 1 }
            .forEach { potion ->
                for (i in potion.items.indices) {
                    for (j in i until potion.items.size) {
                        onOpHeldU(potion.items[i], potion.items[j]) { decant(potion, it) }
                    }
                }
            }
    }

    private fun ProtectedAccess.decant(potion: PotionRow, ev: HeldUEvents.Type) {
        val max = potion.items.size
        val sourceDoses = potion.doses(ev.first.id)
        val targetDoses = potion.doses(ev.second.id)

        if (sourceDoses == max || targetDoses == max) {
            mes(Constants.dm_default)
            return
        }

        val total = sourceDoses + targetDoses
        val filled = minOf(max, total)
        val left = total - filled

        val target = invReplaceSlot(inv, ev.secondSlot, 1, potion.items[max - filled])
        if (target.failure) {
            return
        }

        val sourceReplacement = if (left > 0) potion.items[max - left] else potion.empty
        if (invReplaceSlot(inv, ev.firstSlot, 1, sourceReplacement).failure) {
            invReplaceSlot(inv, ev.secondSlot, 1, ev.second)
            return
        }

        mes("You have combined the liquid into $filled doses.")
    }

    private fun PotionRow.doses(itemId: Int): Int =
        items.size - items.indexOfFirst { it.id == itemId }
}
