.class public La/a/b/a;
.super Ljava/lang/Object;

# A receiver, declared in the manifest and named the same as a package segment —
# the kind of collision that a naive name-based lookup gets wrong.

.method public constructor <init>()V
    .locals 0
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method

.method public onReceive(Landroid/content/Context;Landroid/content/Intent;)V
    .locals 2
    const-string v0, "action"
    const-string v1, "com.example.ACTION_BOOT"
    invoke-virtual {p1, v0}, Landroid/content/Intent;->getStringExtra(Ljava/lang/String;)Ljava/lang/String;
    move-result-object v2
    return-void
.end method
