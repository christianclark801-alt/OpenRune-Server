package org.rsmod.content.other.soulforge.pack

import dev.openrune.cache.tools.tasks.CacheTask
import dev.openrune.pack.PluginPack

class SoulForgePluginPack : PluginPack() {
    override fun extraTasks(): List<CacheTask> = listOf(SoulEssenceCollectionLogTask())
}
