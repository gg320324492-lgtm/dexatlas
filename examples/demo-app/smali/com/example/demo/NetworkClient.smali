.class public final Lcom/example/demo/NetworkClient;
.super Ljava/lang/Object;
.source "NetworkClient.java"

.method public static post(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;
    .locals 2
    new-instance v0, Ljava/net/URL;
    invoke-direct {v0, p0}, Ljava/net/URL;-><init>(Ljava/lang/String;)V
    invoke-virtual {v0}, Ljava/net/URL;->openConnection()Ljava/net/URLConnection;
    move-result-object v0
    check-cast v0, Ljava/net/HttpURLConnection;
    invoke-virtual {v0, p1}, Ljava/net/HttpURLConnection;->setRequestProperty(Ljava/lang/String;Ljava/lang/String;)V
    const/4 v1, 0x1
    invoke-virtual {v0, v1}, Ljava/net/HttpURLConnection;->setDoOutput(Z)V
    const/16 v1, 0x3e8
    invoke-virtual {v0, v1}, Ljava/net/HttpURLConnection;->setConnectTimeout(I)V
    const-string v1, "{}"
    return-object v1
.end method
