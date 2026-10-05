package org.rsmod.content.other.admintool.world

import jakarta.inject.Inject
import jakarta.inject.Singleton
import java.nio.file.Files
import java.nio.file.Path

/**
 * Writes the loc types behind in-game renames: a gameval per renamed loc next to the saved world,
 * and an `[[object]]` config in the admin tool's pack that copies the original type under the new
 * name. Both are regenerated from the whole [AdminWorld] each time, so deleted locs drop out. They
 * take effect after `mergePluginGamevals` + `buildCache` and a restart.
 */
@Singleton
class LocRenameFiles(private val gamevals: Path, private val config: Path) {
    @Inject constructor() : this(GAMEVALS, CONFIG)

    fun write(world: AdminWorld) {
        val renamed = world.locs.filter { it.renamedType != null }
        if (renamed.isEmpty()) {
            Files.deleteIfExists(gamevals)
            Files.deleteIfExists(config)
            return
        }
        val ids = renamed.map { it.renamedType!!.removePrefix("loc.") }

        val gamevalLines = buildList {
            add("[gamevals.loc]")
            ids.forEach { key -> add("$key = ${key.removePrefix("admin_loc_")}") }
        }
        val configLines = buildList {
            renamed.forEach { spawn ->
                add("[[object]]")
                add("id = \"${spawn.renamedType}\"")
                add("inherit = \"${spawn.type}\"")
                spawn.renamedName?.let { add("name = \"${escape(it)}\"") }
                spawn.customOption?.let { add("option1 = \"${escape(it)}\"") }
                add("")
            }
        }
        writeLines(gamevals, gamevalLines)
        writeLines(config, configLines)
    }

    private fun writeLines(file: Path, lines: List<String>) {
        Files.createDirectories(file.parent)
        Files.write(file, lines.joinToString("\n", postfix = "\n").toByteArray())
    }

    private fun escape(text: String): String = text.replace("\\", "\\\\").replace("\"", "\\\"")

    companion object {
        val GAMEVALS: Path = AdminWorldStore.WORLD_DIR.resolve("gamevals.toml")
        val CONFIG: Path =
            Path.of("content", "other", "admin-tool", "pack", "src", "main", "resources", "pack", "configs",
                "admin_renames.toml")
    }
}
