package org.rsmod.content.other.soulforge

import dev.openrune.types.ItemServerType
import jakarta.inject.Inject
import org.rsmod.api.player.hook.PlayerHeldDropWarningHook
import org.rsmod.game.entity.Player
import org.rsmod.game.inv.InvObj

class SoulForgeDropWarning @Inject constructor() : PlayerHeldDropWarningHook {
    override fun dropWarning(player: Player, obj: InvObj, type: ItemServerType): String? =
        dropWarningText(type.name, SoulForgeLevels.level(obj.vars))
}

internal fun dropWarningText(name: String, level: Int): String? =
    if (level > 0) {
        "Dropping your $name will <col=7f0000>permanently remove</col> its +$level Soul Forge level."
    } else {
        null
    }
