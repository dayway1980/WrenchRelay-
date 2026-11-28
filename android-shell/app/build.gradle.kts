plugins {
    id("com.android.application")
}

// These properties are supplied by the existing protected Play signing workflow.
// Defaults preserve the separate com.wrenchrelay.industrial development build.
val configuredPlayApplicationId = providers.gradleProperty("playApplicationId")
    .getOrElse("com.wrenchrelay.industrial")
require(configuredPlayApplicationId in setOf(
    "com.wrenchrelay.industrial", "com.wrenchrelayllc.industrial"
)) { "playApplicationId must match an existing WrenchRelay Industrial package" }

val configuredPlayVersionCode = providers.gradleProperty("playVersionCode")
    .getOrElse("1").let { raw ->
        require(raw.matches(Regex("[1-9][0-9]{0,9}"))) {
            "playVersionCode must be an integer from 1 to 2100000000"
        }
        raw.toIntOrNull()?.takeIf { it <= 2100000000 }
            ?: error("playVersionCode must be an integer from 1 to 2100000000")
    }

android {
    namespace = "com.wrenchrelay.industrial"
    compileSdk = 36

    defaultConfig {
        applicationId = configuredPlayApplicationId
        minSdk = 26
        targetSdk = 36
        versionCode = configuredPlayVersionCode
        versionName = "1.0.0"
    }
}

configurations.configureEach {
    resolutionStrategy {
        force("org.jetbrains.kotlin:kotlin-stdlib:1.8.22")
        force("org.jetbrains.kotlin:kotlin-stdlib-jdk7:1.8.22")
        force("org.jetbrains.kotlin:kotlin-stdlib-jdk8:1.8.22")
    }
}

dependencies {
    implementation("androidx.appcompat:appcompat:1.7.1")
    testImplementation("junit:junit:4.13.2")
}
