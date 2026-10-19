.class public La/a/a;
.super Ljava/lang/Object;

# Obfuscated on purpose: one-letter package, one-letter class, one-letter methods,
# and no .source line. Everything a reader would use to orient themselves is gone,
# which is the point — the tool has to cope with names that carry no information.

.method public constructor <init>()V
    .locals 0
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method

.method public a(Ljava/lang/String;)Ljava/lang/String;
    .locals 2
    new-instance v0, Ljava/lang/StringBuilder;
    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V
    const-string v1, "https://telemetry.example.net/collect?d="
    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    move-result-object v0
    invoke-virtual {v0, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    move-result-object v0
    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v0
    return-object v0
.end method

.method public b()Ljava/lang/String;
    .locals 1
    const-string v0, "a"
    return-object v0
.end method
