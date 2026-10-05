package org.rsmod.content.other.admintool.world

import com.fasterxml.jackson.databind.SerializationFeature
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import com.fasterxml.jackson.module.kotlin.readValue
import jakarta.inject.Inject
import jakarta.inject.Singleton
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.StandardCopyOption

/** Loads and saves the [AdminWorld]; every change is written straight away. */
@Singleton
class AdminWorldStore(private val file: Path) {
    @Inject constructor() : this(FILE)

    private val mapper = jacksonObjectMapper().enable(SerializationFeature.INDENT_OUTPUT)

    val world: AdminWorld by lazy(::load)

    private fun load(): AdminWorld =
        if (Files.exists(file)) mapper.readValue(file.toFile()) else AdminWorld()

    fun save() {
        Files.createDirectories(file.parent)
        val temp = file.resolveSibling("${file.fileName}.tmp")
        mapper.writeValue(temp.toFile(), world)
        Files.move(temp, file, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE)
    }

    companion object {
        val WORLD_DIR: Path = Path.of("content", "other", "admin-tool", "world")
        val FILE: Path = WORLD_DIR.resolve("admin_world.json")
    }
}
