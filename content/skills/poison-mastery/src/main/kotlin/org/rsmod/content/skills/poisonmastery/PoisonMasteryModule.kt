package org.rsmod.content.skills.poisonmastery

import org.rsmod.api.npc.hit.NpcDamageContributor
import org.rsmod.plugin.module.PluginModule

class PoisonMasteryModule : PluginModule() {
    override fun bind() {
        addSetBinding<NpcDamageContributor>(PoisonMasteryXp::class.java)
    }
}
