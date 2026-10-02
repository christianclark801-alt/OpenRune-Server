package org.rsmod.content.other.soulforge

import com.github.michaelbull.logging.InlineLogger
import dev.openrune.ServerCacheManager
import dev.openrune.rscm.RSCM.asRSCM
import dev.openrune.rscm.RSCMType
import dev.openrune.types.aconverted.SpotanimType
import dev.or2.central.account.Rights
import jakarta.inject.Inject
import org.rsmod.api.player.protect.ProtectedAccess
import org.rsmod.api.realm.Realm
import org.rsmod.api.repo.loc.LocRepository
import org.rsmod.api.repo.world.WorldRepository
import org.rsmod.api.script.onGameStartup
import org.rsmod.api.script.onOpLoc1
import org.rsmod.api.script.onOpLoc2
import org.rsmod.api.script.onOpLoc3
import org.rsmod.game.loc.BoundLocInfo
import org.rsmod.game.loc.LocAngle
import org.rsmod.game.loc.LocInfo
import org.rsmod.game.loc.LocShape
import org.rsmod.game.queue.WorldQueueList
import org.rsmod.map.CoordGrid
import org.rsmod.plugin.scripts.PluginScript
import org.rsmod.plugin.scripts.ScriptContext

private const val SOUL_FORGE = "loc.raids_tekton_anvil"
private const val SOUL_SPOTANIM = "spotanim.whisperer_impact_soul_spotanim"
private const val SMOKE_SPOTANIM = "spotanim.smokepuff_large"

private const val OFFSET_X = -2
private const val OFFSET_Z = 2

private const val AMBIENT_INTERVAL = 3
private const val SMOKE_EVERY = 2
private const val SOUL_HEIGHT = 120
private const val SMOKE_HEIGHT = 40

class SoulForgeScript
@Inject
constructor(
    private val realm: Realm,
    private val locRepo: LocRepository,
    private val worldRepo: WorldRepository,
    private val worldQueues: WorldQueueList,
) : PluginScript() {
    private val logger = InlineLogger()

    private var forge: LocInfo? = null
    private var ambientCycle = 0

    private val soulSpotanim by lazy { SpotanimType(SOUL_SPOTANIM.asRSCM(RSCMType.SPOTANIM)) }
    private val smokeSpotanim by lazy { SpotanimType(SMOKE_SPOTANIM.asRSCM(RSCMType.SPOTANIM)) }

    override fun ScriptContext.startup() {
        onGameStartup { spawnForge() }

        onOpLoc1(SOUL_FORGE) { mes("The Soul Forge hums with trapped souls...") }
        onOpLoc2(SOUL_FORGE) { mes("Upgrades are coming soon.") }
        onOpLoc3(SOUL_FORGE) { destroy(it.loc) }
    }

    private fun spawnForge() {
        runCatching {
            val coords = realm.config.spawnCoord.translate(OFFSET_X, OFFSET_Z)
            val loc =
                locRepo.add(
                    coords,
                    SOUL_FORGE,
                    Int.MAX_VALUE,
                    LocAngle.West,
                    LocShape.CentrepieceStraight,
                )
            forge = loc
            scheduleAmbient(loc.centre())
        }.onFailure { logger.warn(it) { "Unable to spawn the Soul Forge; rebuild the cache with buildCache." } }
    }

    private fun scheduleAmbient(centre: CoordGrid) {
        worldQueues.add(AMBIENT_INTERVAL) {
            if (forge == null) {
                return@add
            }
            worldRepo.spotanimMap(soulSpotanim, centre, SOUL_HEIGHT)
            if (ambientCycle++ % SMOKE_EVERY == 0) {
                worldRepo.spotanimMap(smokeSpotanim, centre, SMOKE_HEIGHT)
            }
            scheduleAmbient(centre)
        }
    }

    private suspend fun ProtectedAccess.destroy(loc: BoundLocInfo) {
        if (!player.modLevel.isAtLeast(Rights.ADMINISTRATOR)) {
            mes("Only the owner can destroy this table.")
            return
        }
        val confirmed = choice2("Yes", true, "No", false, title = "Destroy the Soul Forge?")
        if (!confirmed) {
            return
        }
        locRepo.del(loc, Int.MAX_VALUE)
        forge = null
        mes("The Soul Forge collapses into ash.")
    }

    private fun LocInfo.centre(): CoordGrid {
        val type = ServerCacheManager.getObject(id) ?: return coords
        return coords.translate(type.width / 2, type.length / 2)
    }
}
