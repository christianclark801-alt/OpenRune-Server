package org.rsmod.content.other.homeshops.pack

import dev.openrune.cache.tools.tasks.CacheTask
import dev.openrune.pack.PluginPack

class HomeShopsPluginPack : PluginPack() {
    override fun extraTasks(): List<CacheTask> = listOf(HomeShopRowsTask())
}
