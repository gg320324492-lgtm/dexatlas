.class public final Lcom/example/strings/Constants;
.super Ljava/lang/Object;
.source "Constants.java"

# A file that is mostly string constants. Every one of them is a place a reader
# would look for a hardcoded secret, an endpoint, or a leaky identifier — which is
# exactly what the search index is for.

.field public static final BASE_URL:Ljava/lang/String; = "https://api.example.com/v2"

.field public static final STAGING_URL:Ljava/lang/String; = "https://staging.api.example.com/v2"

.field public static final API_KEY:Ljava/lang/String; = "sk_live_PLACEHOLDER_NOT_A_REAL_KEY"

.field public static final FALLBACK_KEY:Ljava/lang/String; = "sk_test_PLACEHOLDER_NOT_A_REAL_KEY"

.method public constructor <init>()V
    .locals 0
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method

.method public static baseUrl()Ljava/lang/String;
    .locals 1
    const-string v0, "https://api.example.com/v2"
    return-object v0
.end method

.method public static stagingUrl()Ljava/lang/String;
    .locals 1
    const-string v0, "https://staging.api.example.com/v2"
    return-object v0
.end method

.method public static apiKey()Ljava/lang/String;
    .locals 1
    const-string v0, "sk_live_PLACEHOLDER_NOT_A_REAL_KEY"
    return-object v0
.end method

.method public static fallbackKey()Ljava/lang/String;
    .locals 1
    const-string v0, "sk_test_PLACEHOLDER_NOT_A_REAL_KEY"
    return-object v0
.end method

.method public static authHeader()Ljava/lang/String;
    .locals 2
    new-instance v0, Ljava/lang/StringBuilder;
    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V
    const-string v1, "Bearer "
    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    move-result-object v0
    invoke-virtual {v0}, Lcom/example/strings/Constants;->apiKey()Ljava/lang/String;
    move-result-object v1
    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    move-result-object v0
    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v0
    return-object v0
.end method

.method public static analyticsEvent()Ljava/lang/String;
    .locals 1
    const-string v0, "screen_view"
    return-object v0
.end method

.method public static errorMessage()Ljava/lang/String;
    .locals 1
    const-string v0, "request_failed_retry_later"
    return-object v0
.end method

.method public static userAgent()Ljava/lang/String;
    .locals 1
    const-string v0, "ExampleApp/7.1.3 (Android 14; Pixel 8)"
    return-object v0
.end method

.method public static buildVariant()Ljava/lang/String;
    .locals 1
    const-string v0, "release"
    return-object v0
.end method
