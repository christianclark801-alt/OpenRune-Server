package org.rsmod.content.other.soulforge.pack

import dev.openrune.OsrsCacheProvider
import dev.openrune.cache.tools.TaskPriority
import dev.openrune.cache.tools.tasks.CacheTask
import dev.openrune.definition.codec.EnumCodec
import dev.openrune.definition.type.EnumType
import dev.openrune.definition.type.StructType
import dev.openrune.filesystem.Cache
import dev.openrune.rscm.RSCM
import io.netty.buffer.Unpooled

/**
 * Appends Soul essence to every category on the collection log's Bosses tab. The log reads its
 * items from cache data (tab struct -> category enum -> category struct -> items enum), so the
 * item has to be written into each boss category's items enum for both client and server.
 */
class SoulEssenceCollectionLogTask : CacheTask() {
    override val priority: TaskPriority
        get() = TaskPriority.END

    override fun init(cache: Cache) {
        val essence = RSCM.getRSCM(SOUL_ESSENCE)
        val enums = mutableMapOf<Int, EnumType>()
        val structs = mutableMapOf<Int, StructType>()
        OsrsCacheProvider.EnumDecoder().load(cache, enums)
        OsrsCacheProvider.StructDecoder().load(cache, structs)

        val categoryList = structs[BOSS_TAB_STRUCT]?.params?.get(TAB_CATEGORY_LIST_PARAM) as? Int
        val categories = categoryList?.let(enums::get) ?: return
        val codec = EnumCodec()

        for (categoryStruct in categories.values.values) {
            val struct = structs[categoryStruct as? Int ?: continue] ?: continue
            val itemsEnumId = struct.params?.get(CATEGORY_ITEMS_PARAM) as? Int ?: continue
            val items = enums[itemsEnumId] ?: continue
            if (essence in items.values.values) {
                continue
            }
            val nextKey = (items.values.keys.maxOrNull() ?: -1) + 1
            val patched = items.copy(values = (items.values + (nextKey to essence)).toMutableMap())
            patched.id = itemsEnumId
            val buffer = Unpooled.buffer()
            with(codec) { buffer.encode(patched) }
            val bytes = ByteArray(buffer.readableBytes()).also(buffer::readBytes)
            cache.write(CONFIG_INDEX, ENUM_ARCHIVE, itemsEnumId, bytes)
        }
    }

    private companion object {
        const val SOUL_ESSENCE = "obj.soul_essence"
        const val BOSS_TAB_STRUCT = 471
        const val TAB_CATEGORY_LIST_PARAM = 683
        const val CATEGORY_ITEMS_PARAM = 690
        const val CONFIG_INDEX = 2
        const val ENUM_ARCHIVE = 8
    }
}
