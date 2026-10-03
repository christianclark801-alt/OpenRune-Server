package org.rsmod.api.game.process.player

import dev.openrune.ServerCacheManager
import net.rsprot.protocol.game.outgoing.inv.UpdateInvFull
import net.rsprot.protocol.game.outgoing.inv.UpdateInvPartial
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.parallel.Execution
import org.junit.jupiter.api.parallel.ExecutionMode
import org.junit.jupiter.api.parallel.ResourceLock
import org.rsmod.api.player.hook.PlayerInvPreTransmitHook
import org.rsmod.api.player.startInvTransmit
import org.rsmod.game.client.Client
import org.rsmod.game.entity.Player
import org.rsmod.game.entity.PlayerList
import org.rsmod.game.entity.util.ShuffledPlayerList
import org.rsmod.game.inv.InvObj

@Execution(ExecutionMode.SAME_THREAD)
@ResourceLock("ServerCacheManager")
class PlayerInvUpdateProcessorTest {
    @Test
    fun `pre-transmit hook edits ship in the same process call as the change that caused them`() {
        val log = mutableListOf<String>()
        val player = Player().apply { client = RecordingClient(log) }
        val inv = player.invMap.getOrPut("inv.inv")
        val mirror = player.invMap.getOrPut("inv.bank")
        player.inv = inv
        player.startInvTransmit(inv)
        player.startInvTransmit(mirror)

        val hook = PlayerInvPreTransmitHook { p ->
            log += "hook"
            if (p.inv.hasModifiedSlots()) {
                mirror[0] = InvObj("obj.coins", 1)
            }
        }
        val processor =
            PlayerInvUpdateProcessor(
                players = ShuffledPlayerList(PlayerList()),
                exceptionHandler = { t, _ -> throw t },
                invUpdateHooks = emptySet(),
                preTransmitHooks = setOf(hook),
            )

        processor.process(player)
        processor.cleanUp()
        log.clear()

        inv[0] = InvObj("obj.coins", 1)
        processor.process(player)
        processor.cleanUp()

        assertEquals(listOf("hook", "partial:${inv.type.id}", "partial:${mirror.type.id}"), log)
    }

    private class RecordingClient(private val log: MutableList<String>) : Client<Any, Any> {
        override fun write(message: Any) {
            when (message) {
                is UpdateInvPartial -> log += "partial:${message.inventoryId}"
                is UpdateInvFull -> log += "full:${message.inventoryId}"
            }
        }

        override fun close() {}

        override fun read(player: Player) {}

        override fun flush() {}

        override fun flushHighPriority() {}

        override fun unregister(service: Any, player: Player) {}
    }

    companion object {
        @JvmStatic
        @BeforeAll
        fun cache() {
            ServerCacheManager.init(240).close()
        }
    }
}
