.class public La/a/b;
.super Ljava/lang/Object;

.method public constructor <init>()V
    .locals 0
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method

.method public a(Ljava/lang/String;)V
    .locals 2
    const-string v0, "sms_body_prefix"
    const-string v1, "generic_text_message"
    invoke-virtual {p0, v1, v0}, Ljava/lang/String;->replace(Ljava/lang/CharSequence;Ljava/lang/CharSequence;)Ljava/lang/String;
    move-result-object v0
    return-void
.end method

.method public c()I
    .locals 1
    const/16 v0, 0x1
    return v0
.end method
