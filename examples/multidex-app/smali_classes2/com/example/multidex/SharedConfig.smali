.class public Lcom/example/multidex/SharedConfig;
.super Ljava/lang/Object;
.source "SharedConfig.java"

# The same fully-qualified name also exists in classes.dex. Whichever is found
# first, the same one must be found every time — resolution cannot depend on
# directory iteration order.

.method public constructor <init>()V
    .locals 0
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method

.method public static origin()Ljava/lang/String;
    .locals 1
    const-string v0, "secondary-dex"
    return-object v0
.end method

.method public static timeoutMillis()I
    .locals 1
    const/16 v0, 0x1388
    return v0
.end method
