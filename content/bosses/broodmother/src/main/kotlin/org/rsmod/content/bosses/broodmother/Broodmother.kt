package org.rsmod.content.bosses.broodmother

import jakarta.inject.Inject
import org.rsmod.api.bosses.dsl.*
import org.rsmod.api.bosses.runtime.BossCombat
import org.rsmod.api.bosses.runtime.BossDeps
import org.rsmod.api.bosses.runtime.BossPluginScript
import org.rsmod.api.bosses.spec.Effect
import org.rsmod.plugin.scripts.ScriptContext

class Broodmother @Inject constructor(deps: BossDeps) : BossPluginScript(deps) {

    override val spec = boss("npc.broodmother") {

        stats(attackRate = 5)

        val bite = ability("bite") {
            anim(ATTACK_SEQ)
            hit {
                damage(0..BITE_MAX_HIT).roll()
                type(Melee)
            }
            poison(damage = BITE_POISON, chance = 1, outOf = 3)
        }

        val spit = ability("poison_spit") {
            anim(ATTACK_SEQ)
            projectile(
                spotanim = SPIT_PROJECTILE,
                travel = SPIT_TRAVEL,
                hit = Effect.Hit(damage = Roll(0..SPIT_MAX_HIT), type = Ranged),
            )
            poison(damage = SPIT_POISON)
        }

        phase("combat") {
            forceEveryAttacks(SPIT_MIN_ATTACKS, SPIT_MAX_ATTACKS, spit)
            weightedSelectorRandom {
                +random(bite, weight = 4, requires = WithinMeleeRange)
                +random(spit, weight = 1)
            }
        }
    }

    override fun ScriptContext.startup() {
        BossCombat.register(this, spec, deps)
    }

    private companion object {
        const val ATTACK_SEQ = "seq.broodmother_attack"
        const val SPIT_PROJECTILE = "spotanim.adamant_dragon_poisonball"
        const val SPIT_TRAVEL = "projanim.dragonfire"

        const val BITE_MAX_HIT = 28
        const val BITE_POISON = 8
        const val SPIT_MAX_HIT = 22
        const val SPIT_POISON = 10
        const val SPIT_MIN_ATTACKS = 5
        const val SPIT_MAX_ATTACKS = 8
    }
}
