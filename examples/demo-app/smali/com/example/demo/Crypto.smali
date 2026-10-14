.class public final Lcom/example/demo/Crypto;
.super Ljava/lang/Object;
.source "Crypto.java"

.method public static sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;
    .locals 2
    new-instance v0, Ljava/lang/StringBuilder;
    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V
    invoke-virtual {v0, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    move-result-object v0
    invoke-virtual {v0, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    move-result-object v0
    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v0
    return-object v0
.end method

.method public static obfuscate(Ljava/lang/String;)Ljava/lang/String;
    .locals 2
    :try_start
    invoke-virtual {p0}, Ljava/lang/String;->toUpperCase()Ljava/lang/String;
    move-result-object v0
    :try_end
    .catch Ljava/lang/Exception; {:try_start .. :try_end} :catch
    return-object v0
    :catch
    move-exception v1
    const-string v0, "obfuscation_failed"
    return-object v0
.end method

.method public static digestOf(Ljava/lang/String;)Ljava/lang/String;
    .locals 1
    const-string v0, "SHA-256"
    invoke-static {v0}, Ljava/security/MessageDigest;->getInstance(Ljava/lang/String;)Ljava/security/MessageDigest;
    move-result-object v0
    invoke-virtual {v0, p0}, Ljava/security/MessageDigest;->digest(Ljava/lang/String;)Ljava/lang/String;
    move-result-object v0
    invoke-virtual {v0}, Ljava/lang/String;->toLowerCase()Ljava/lang/String;
    move-result-object v0
    return-object v0
.end method
