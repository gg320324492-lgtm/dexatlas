.class public Lcom/example/multidex/SharedConfig;
.super Ljava/lang/Object;
.source "SharedConfig.java"

# This class exists in BOTH dexes on purpose. A name that appears twice must resolve
# to the same file on every call, and the primary dex wins because the directories
# are searched in sorted order.

.method public constructor <init>()V
    .locals 0
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method

.method public static origin()Ljava/lang/String;
    .locals 1
    const-string v0, "primary-dex"
    return-object v0
.end method

.method public static timeoutMillis()I
    .locals 1
    const/16 v0, 0x3e8
    return v0
.end method
