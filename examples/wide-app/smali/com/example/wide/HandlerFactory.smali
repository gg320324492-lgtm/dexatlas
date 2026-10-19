.class public Lcom/example/wide/HandlerFactory;
.super Ljava/lang/Object;
.source "HandlerFactory.java"

# Calls both implementations, so a cross-reference query for either of them has to
# find this class as a caller. That is what makes the call graph worth having.

.method public constructor <init>()V
    .locals 0
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method

.method public static create(Ljava/lang/String;)Lcom/example/wide/Handler;
    .locals 1
    const-string v0, "json"
    invoke-virtual {p0, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_not_json

    new-instance v0, Lcom/example/wide/JsonHandler;
    invoke-direct {v0}, Lcom/example/wide/JsonHandler;-><init>()V
    return-object v0

    :cond_not_json
    new-instance v0, Lcom/example/wide/XmlHandler;
    invoke-direct {v0}, Lcom/example/wide/XmlHandler;-><init>()V
    return-object v0
.end method

.method public static dispatch(Lcom/example/wide/Handler;Ljava/lang/String;)Ljava/lang/String;
    .locals 1
    invoke-interface {p0, p1}, Lcom/example/wide/Handler;->handle(Ljava/lang/String;)Ljava/lang/String;
    move-result-object v0
    return-object v0
.end method
