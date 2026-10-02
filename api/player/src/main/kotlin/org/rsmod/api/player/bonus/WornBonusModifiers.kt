package org.rsmod.api.player.bonus

import dev.openrune.types.ItemServerType
import org.rsmod.game.inv.InvObj

public data class ObjBonus(
    val meleeStr: Int = 0,
    val rangedStr: Int = 0,
    val magicDmg: Int = 0,
)

public object WornBonusModifiers {
    @Volatile public var perObj: (InvObj, ItemServerType) -> ObjBonus? = { _, _ -> null }
}
