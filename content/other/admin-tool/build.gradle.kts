plugins {
    id("base-conventions")
}

dependencies {
    implementation(projects.api.pluginCommons)
    implementation(projects.api.registry)
    implementation(libs.jackson.databind)
    implementation(libs.jackson.module.kotlin)
}
