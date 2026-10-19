.class public Lcom/example/multidex/SecondaryHelper;
.super Ljava/lang/Object;
.source "SecondaryHelper.java"

# Lives in classes2.dex. Apktool decodes that dex into smali_classes2/, a sibling of
# smali/ rather than a child of it — the layout the Smali fallback must find.

.method public constructor <init>()V
    .locals 0
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method

.method public static secondaryEndpoint()Ljava/lang/String;
    .locals 1
    const-string v0, "https://secondary.example.com/api/v2/sync"
    return-object v0
.end method

.method public static describe()Ljava/lang/String;
    .locals 1
    const-string v0, "secondary-dex"
    return-object v0
.end method
