package org.rsmod.content.other.soulforge

import org.rsmod.api.death.NpcDeathKillHook
import org.rsmod.api.npc.hit.NpcDamageContributor
import org.rsmod.api.npc.hit.modifier.PlayerNpcDamageModifier
import org.rsmod.plugin.module.PluginModule

class SoulForgeModule : PluginModule() {
    override fun bind() {
        addSetBinding<NpcDeathKillHook>(SoulEssenceDropHook::class.java)
        addSetBinding<NpcDamageContributor>(SoulLifestealContributor::class.java)
        addSetBinding<PlayerNpcDamageModifier>(SoulDamageModifier::class.java)
    }
}
