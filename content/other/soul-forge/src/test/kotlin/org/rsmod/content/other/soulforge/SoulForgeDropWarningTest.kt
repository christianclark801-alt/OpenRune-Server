package org.rsmod.content.other.soulforge

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Test

class SoulForgeDropWarningTest {
    @Test
    fun `forged items warn with their level`() {
        assertEquals(
            "Dropping your Torva full helm will <col=7f0000>permanently remove</col> its +2 Soul Forge level.",
            dropWarningText("Torva full helm", 2),
        )
    }

    @Test
    fun `unforged items drop without a warning`() {
        assertNull(dropWarningText("Torva full helm", 0))
    }
}
