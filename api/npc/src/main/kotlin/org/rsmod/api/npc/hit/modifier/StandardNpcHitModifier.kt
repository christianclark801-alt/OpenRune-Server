package org.rsmod.api.npc.hit.modifier

import jakarta.inject.Inject
import kotlin.math.absoluteValue
import kotlin.math.min
import org.rsmod.api.npc.events.NpcHitEvents
import org.rsmod.api.npc.hit.isStyleImmuneTo
import org.rsmod.events.EventBus
import org.rsmod.game.entity.Npc
import org.rsmod.game.entity.PlayerList
import org.rsmod.game.entity.player.PlayerUid
import org.rsmod.game.hit.HitBuilder

public class StandardNpcHitModifier
@Inject
constructor(
    private val eventBus: EventBus,
    private val playerList: PlayerList,
    private val playerModifiers: Set<PlayerNpcDamageModifier>,
) : NpcHitModifier {
    override fun HitBuilder.modify(target: Npc) {
        target.publishEvent(this)
        target.applyPlayerModifiers(this)
        target.applyStyleImmunity(this)
        target.applyFlatArmour(this)
    }

    private fun Npc.publishEvent(hit: HitBuilder) {
        val event = NpcHitEvents.Modify(this, hit)
        eventBus.publish(event)
    }

    private fun Npc.applyPlayerModifiers(hit: HitBuilder) {
        val uid = hit.sourceUid
        if (!hit.isFromPlayer || uid == null || playerModifiers.isEmpty()) {
            return
        }
        val source = PlayerUid(uid).resolve(playerList) ?: return
        for (modifier in playerModifiers) {
            modifier.modify(hit, this, source)
        }
    }

    private fun Npc.applyStyleImmunity(hit: HitBuilder) {
        if (isStyleImmuneTo(hit.type)) {
            hit.damage = 0
        }
    }

    private fun Npc.applyFlatArmour(hit: HitBuilder) {
        val armour = vars["varn.flat_armour"]

        if (armour > 0) {
            val capped = min(armour.absoluteValue, hit.damage)
            vars["varn.flat_armour"] -= capped
            hit.damage -= capped
        }

        if (armour < 0) {
            vars["varn.flat_armour"] = 0
            hit.damage += armour.absoluteValue
        }
    }
}
