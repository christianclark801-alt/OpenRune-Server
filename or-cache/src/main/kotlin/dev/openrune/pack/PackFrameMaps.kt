package dev.openrune.pack

import dev.openrune.cache.tools.incremental.PackUnit
import dev.openrune.cache.tools.tasks.CacheTask
import dev.openrune.cache.util.getFiles
import dev.openrune.filesystem.Cache
import java.io.File
import java.nio.file.Files

/**
 * Packs animation frame maps (skeletons) into index 1. Each `<id>.dat` under [frameMapDirectory]
 * is written as-is to group `id`, file 0; frames that use it reference the same id.
 */
class PackFrameMaps(private val frameMapDirectory: File) : CacheTask() {

    override fun init(cache: Cache) {
        val files = getFiles(frameMapDirectory, "dat")
        if (files.isEmpty()) return

        val root = frameMapDirectory.absoluteFile
        val units = files.map { file ->
            PackUnit(key = file.absoluteFile.relativeTo(root).path.replace('\\', '/'), source = file)
        }

        incremental.run(
            task = this,
            scope = frameMapDirectory.absolutePath,
            label = "Packing Frame Maps",
            cache = cache,
            units = units,
        ) { packCache, unit ->
            val file = unit.sources.single()
            val id = file.nameWithoutExtension.toIntOrNull()
                ?: error("Frame map ${file.name} must be named after its numeric id")
            packCache.write(FRAME_MAPS, id, 0, Files.readAllBytes(file.toPath()))
        }
    }

    private companion object {
        const val FRAME_MAPS = 1
    }
}
