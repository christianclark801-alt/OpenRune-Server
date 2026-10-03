package org.rsmod.content.other.special.weapons.ranged

import dev.openrune.rscm.RSCM
import dev.openrune.rscm.RSCMType
import jakarta.inject.Inject
import org.rsmod.api.combat.commons.CombatAttack
import org.rsmod.api.combat.manager.RangedAmmoManager
import org.rsmod.api.config.constants
import org.rsmod.api.config.refs.params
import org.rsmod.api.player.protect.ProtectedAccess
import org.rsmod.api.player.righthand
import org.rsmod.api.weapons.RangedWeapon
import org.rsmod.api.weapons.WeaponAttackManager
import org.rsmod.api.weapons.WeaponMap
import org.rsmod.api.weapons.WeaponRepository
import org.rsmod.game.entity.Npc
import org.rsmod.game.entity.Player
import org.rsmod.game.type.getInvObj

class HolyWaterWeapons @Inject constructor(private val ammunition: RangedAmmoManager) : WeaponMap {
    override fun WeaponRepository.register(manager: WeaponAttackManager) {
        register("obj.holy_water", HolyWater(manager, ammunition))
    }

    private class HolyWater(
        private val manager: WeaponAttackManager,
        private val ammunition: RangedAmmoManager,
    ) : RangedWeapon {
        override suspend fun ProtectedAccess.attack(
            target: Npc,
            attack: CombatAttack.Ranged,
        ): Boolean {
            val weaponType = getInvObj(attack.weapon)

            val travelSpotanim = weaponType.paramOrNull(params.proj_travel)
            if (travelSpotanim == null) {
                manager.stopCombat(this)
                mes("You are unable to fire your ammunition.")
                return true
            }

            manager.playWeaponFx(this, attack)

            val launchSpotanim =
                weaponType.paramOrNull(params.proj_launch)?.let {
                    RSCM.getReverseMapping(RSCMType.SPOTANIM, it.id)
                }
            spotanim(launchSpotanim, height = 96, slot = constants.spotanim_slot_combat)

            val travelSpotanimName = RSCM.getReverseMapping(RSCMType.SPOTANIM, travelSpotanim.id)
            val projanim =
                manager.spawnProjectile(this, target, travelSpotanimName, "projanim.thrown")
            val (serverDelay, clientDelay) = projanim.durations

            ammunition.useThrownWeapon(player, weaponType, target.coords, dropDelay = serverDelay)

            val damage = manager.rollRangedDamage(this, target, attack)
            manager.giveCombatXp(this, target, attack, damage)
            manager.queueRangedHit(this, target, null, damage, clientDelay, serverDelay)
            HolyWaterPoison.apply(target, serverDelay)

            if (player.righthand == null) {
                mes("That was your last one!")
                return true
            }

            manager.continueCombat(this, target)
            return true
        }

        override suspend fun ProtectedAccess.attack(
            target: Player,
            attack: CombatAttack.Ranged,
        ): Boolean = false
    }
}
