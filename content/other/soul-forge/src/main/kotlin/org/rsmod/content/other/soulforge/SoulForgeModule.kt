package org.rsmod.content.other.soulforge

import org.rsmod.api.death.NpcDeathKillHook
import org.rsmod.plugin.module.PluginModule

class SoulForgeModule : PluginModule() {
    override fun bind() {
        addSetBinding<NpcDeathKillHook>(SoulEssenceDropHook::class.java)
    }
}
