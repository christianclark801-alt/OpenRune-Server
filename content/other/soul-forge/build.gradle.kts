plugins {
    id("base-conventions")
}

dependencies {
    implementation(libs.guice)
    implementation(projects.api.config)
    implementation(projects.api.death)
    implementation(projects.api.player)
    implementation(projects.api.playerOutput)
    implementation(projects.api.pluginCommons)
    implementation(projects.api.random)
    implementation(projects.api.realm)
    implementation(projects.api.repo)
    implementation(projects.content.interfaces.collectionLog)
    implementation(projects.engine.game)
    implementation(projects.engine.plugin)
}
