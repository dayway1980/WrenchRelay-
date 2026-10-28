plugins {
    id("com.android.application")
}

android {
    namespace = "com.wrenchrelay.industrial"
    compileSdk = 36

    defaultConfig {
        // HOLD: Confirm this exact applicationId against the Play Console app before signing/upload.
        // Earlier records mention com.wrenchrelayllc.industrial; do not blindly change identifiers.
        // Play signing candidate may override identity only via an explicitly verified
        // manual release workflow; normal QA builds retain the original values.
        val playApplicationId = providers.gradleProperty("playApplicationId").orNull
        val playVersionCode = providers.gradleProperty("playVersionCode").orNull
        require(playApplicationId == null || playApplicationId in setOf(
            "com.wrenchrelay.industrial", "com.wrenchrelayllc.industrial"
        )) { "Unrecognized Play package candidate" }
        applicationId = playApplicationId ?: "com.wrenchrelay.industrial"
        minSdk = 26
        targetSdk = 36
        versionCode = playVersionCode?.toIntOrNull()?.also {
            require(it > 0) { "versionCode must be positive" }
        } ?: if (playVersionCode == null) 1 else error("versionCode must be a positive integer")
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
