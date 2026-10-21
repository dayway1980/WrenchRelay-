plugins {
    id("com.android.application")
}

android {
    namespace = "com.wrenchrelay.industrial"
    compileSdk = 36

    defaultConfig {
        // HOLD: Confirm this exact applicationId against the Play Console app before signing/upload.
        // Earlier records mention com.wrenchrelayllc.industrial; do not blindly change identifiers.
        applicationId = "com.wrenchrelay.industrial"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
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
