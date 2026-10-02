plugins {
    id("base-conventions")
}

dependencies {
    implementation(projects.api.pluginCommons)
    implementation(projects.api.realm)
}

// Fixed name so ExternalPluginLoader always sees this as source "home-plugin" across rebuilds.
tasks.jar {
    archiveFileName.set("home-plugin.jar")
}

// Copies the jar into the repo-root `plugins/` directory, where it is auto-loaded at boot.
tasks.register<Copy>("deployPlugin") {
    from(tasks.jar)
    into(rootProject.layout.projectDirectory.dir("plugins"))
}
