plugins {
    id("base-conventions")
}

dependencies {
    implementation(libs.guice)
    implementation(projects.api.combat.combatCommons)
    implementation(projects.api.config)
    implementation(projects.api.npc)
    implementation(projects.api.mechanics.statusEffects)
    implementation(projects.api.player)
    implementation(projects.api.pluginCommons)
    implementation(projects.api.weapons)
    implementation(projects.content.other.soulForge)
    implementation(projects.engine.game)
    implementation(projects.engine.plugin)
}
