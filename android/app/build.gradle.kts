plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "page.codeberg.kirifestung.stungkir"
    compileSdk = 35

    defaultConfig {
        applicationId = "page.codeberg.kirifestung.stungkir"
        minSdk = 26
        targetSdk = 35
        versionCode = 3
        versionName = "0.1.2"
    }

    // Ключ подписи лежит здесь же, но сам зашифрован паролем, а пароль - только в секретах GitHub
    // (ANDROID_KEYSTORE_PASSWORD). Без пароля релиз подписывается отладочным ключом - годится
    // для своих проверок, но поверх версии из «Релизов» такая сборка не встанет.
    val keyPassword: String? = System.getenv("ANDROID_KEYSTORE_PASSWORD")?.trim()?.takeIf { it.isNotBlank() }
    signingConfigs {
        if (keyPassword != null) {
            create("release") {
                storeFile = file("stungkir-release.keystore")
                storePassword = keyPassword
                keyAlias = "stungkir"
                this.keyPassword = keyPassword
            }
        }
    }

    buildTypes {
        getByName("release") {
            isMinifyEnabled = false
            signingConfig = if (keyPassword != null) signingConfigs.getByName("release") else signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    lint {
        // проверки Android-стиля не должны останавливать сборку (доступ ко всем файлам нужен нарочно)
        checkReleaseBuilds = false
        abortOnError = false
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.10.01")
    implementation(composeBom)
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-core")
    testImplementation("junit:junit:4.13.2")
}

// русские имена файлов в проверках
tasks.withType<Test> {
    systemProperty("file.encoding", "UTF-8")
    jvmArgs("-Dsun.jnu.encoding=UTF-8")
    environment("LC_ALL", "C.UTF-8")
}
