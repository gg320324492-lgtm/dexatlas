.class public Lcom/example/demo/MainActivity;
.super Landroid/app/Activity;
.source "MainActivity.java"

# direct instance fields
.field private static final TAG:Ljava/lang/String; = "MainActivity"
.field private endpoint:Ljava/lang/String;

.method public constructor <init>()V
    .locals 0
    invoke-direct {p0}, Landroid/app/Activity;-><init>()V
    const-string p0, "https://api.example.com/v1"
    iput-object p0, p0, Lcom/example/demo/MainActivity;->endpoint:Ljava/lang/String;
    return-void
.end method

.method protected onCreate(Landroid/os/Bundle;)V
    .locals 2
    invoke-super {p0, p1}, Landroid/app/Activity;->onCreate(Landroid/os/Bundle;)V
    const-string v0, "api_key"
    const-string v1, "sk_live_2f8a91c4e7b3"
    invoke-static {v0, v1}, Lcom/example/demo/Crypto;->sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;
    move-result-object v0
    iget-object v1, p0, Lcom/example/demo/MainActivity;->endpoint:Ljava/lang/String;
    invoke-static {v1, v0}, Lcom/example/demo/NetworkClient;->post(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;
    move-result-object v0
    invoke-static {v0}, Lcom/example/demo/MainActivity;->describe(Ljava/lang/String;)Ljava/lang/String;
    move-result-object v0
    invoke-static {v0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    return-void
.end method

.method public static describe(Ljava/lang/String;)Ljava/lang/String;
    .locals 3
    new-instance v0, Ljava/lang/StringBuilder;
    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V
    const-string v1, "response: "
    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    move-result-object v0
    invoke-virtual {v0, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    move-result-object v0
    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v0
    return-object v0
.end method
