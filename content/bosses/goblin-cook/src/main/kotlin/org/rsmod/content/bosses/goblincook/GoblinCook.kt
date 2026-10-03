package org.rsmod.content.bosses.goblincook

import dev.openrune.rscm.RSCM.asRSCM
import dev.openrune.rscm.RSCMType
import dev.openrune.types.aconverted.SpotanimType
import jakarta.inject.Inject
import org.rsmod.api.bosses.dsl.*
import org.rsmod.api.bosses.runtime.BossCombat
import org.rsmod.api.bosses.runtime.BossDeps
import org.rsmod.api.bosses.runtime.BossPluginScript
import org.rsmod.api.bosses.runtime.lob
import org.rsmod.api.combat.commons.player.finishNpcHit
import org.rsmod.api.player.isValidTarget
import org.rsmod.api.player.output.mes
import org.rsmod.api.player.stat.hitpoints
import org.rsmod.game.entity.Npc
import org.rsmod.game.entity.Player
import org.rsmod.game.hit.HitType
import org.rsmod.plugin.scripts.ScriptContext

class GoblinCook @Inject constructor(deps: BossDeps) : BossPluginScript(deps) {

    override val spec = boss("npc.goblin_cook_boss") {

        stats(attackRate = 5)

        val melee = ability("melee") {
            anim(ATTACK_SEQ)
            hit {
                damage(0..MELEE_MAX_HIT).roll()
                type(Melee)
            }
        }

        val knifeThrow = ability("knife_throw") {
            anim(ATTACK_SEQ)
            say("Order up!")
            include(external(KNIFE_THROW_HANDLER))
        }

        val tasteTest = ability("taste_test") {
            setVarn(TASTING_VARN, 1)
            say("Mmm... needs more salt!")
            anim(TASTE_SEQ)
            wait(TASTE_TICKS)
            healSelf(TASTE_HEAL)
            setVarn(TASTING_VARN, 0)
        }

        val spoiled = ability("spoiled") {
            interrupt()
            setVarn(TASTING_VARN, 0)
            say("Bah! You've spoiled my soup!")
        }

        onIncomingHit(spoiled, requires = varnIs(TASTING_VARN, 1))

        phase("combat") {
            forceWhen(HpBelow(TASTE_HP_FRACTION), tasteTest, once = true)
            forceEveryAttacks(KNIFE_MIN_ATTACKS, KNIFE_MAX_ATTACKS, knifeThrow)
            weightedSelectorRandom {
                +random(melee, weight = 4, requires = WithinMeleeRange)
                +random(knifeThrow, weight = 1)
            }
        }
    }

    override fun ScriptContext.startup() {
        BossCombat.register(this, spec, deps)
        deps.extensionRegistry.register(KNIFE_THROW_HANDLER) { _, npc, target, _ ->
            knifeThrow(npc, target)
        }
    }

    private fun knifeThrow(npc: Npc, target: Player) {
        if (!target.isValidTarget()) return

        val landingTile = target.coords
        deps.worldRepo.spotanimMap(SpotanimType(TELEGRAPH_SHADOW), landingTile)
        deps.lob(
            npc = npc,
            targetTile = landingTile,
            targetUid = target.uid,
            spotanim = KNIFE_TRAVEL,
            startHeight = KNIFE_START_HEIGHT,
            endHeight = 0,
            delay = KNIFE_PROJ_DELAY,
            travel = KNIFE_PROJ_TRAVEL,
            curve = KNIFE_PROJ_CURVE,
            landTicks = KNIFE_LAND_TICKS,
            landGfx = KNIFE_LAND_GFX,
        ) { player ->
            if (player.coords == landingTile) {
                player.mes("The Goblin COOK's knife lands right on top of you!")
                player.finishNpcHit(npc, 1, HitType.Typeless, player.hitpoints, deps.playerHitModifier)
            }
        }
    }

    private companion object {
        const val ATTACK_SEQ = "seq.slice_surface_goblin_squat_unarmed_attack"
        const val TASTE_SEQ = "seq.slice_surface_goblin_defend"
        const val TASTING_VARN = "varn.goblin_cook_tasting"
        const val KNIFE_THROW_HANDLER = "goblin_cook.knife_throw"

        const val MELEE_MAX_HIT = 10
        const val TASTE_HP_FRACTION = 0.3
        const val TASTE_TICKS = 4
        const val TASTE_HEAL = 25
        const val KNIFE_MIN_ATTACKS = 6
        const val KNIFE_MAX_ATTACKS = 9

        const val KNIFE_LAND_TICKS = 4
        const val KNIFE_START_HEIGHT = 200
        const val KNIFE_PROJ_DELAY = 30
        const val KNIFE_PROJ_TRAVEL = 90
        const val KNIFE_PROJ_CURVE = 30

        val TELEGRAPH_SHADOW = "spotanim.gargboss_debris_shadow_120".asRSCM(RSCMType.SPOTANIM)
        val KNIFE_LAND_GFX = "spotanim.emote_duststamp_spot".asRSCM(RSCMType.SPOTANIM)
        val KNIFE_TRAVEL = "spotanim.goblin_cook_knife_travel".asRSCM(RSCMType.SPOTANIM)
    }
}
