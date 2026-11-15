package com.example.demo;

import java.net.HttpURLConnection;
import java.net.URL;

/* loaded from: classes.dex */
public final class NetworkClient {
    /* JADX WARN: Type inference failed for: r0v2, types: [java.lang.String, java.net.HttpURLConnection] */
    public static String post(String str, String str2) {
        ?? r0 = (HttpURLConnection) new URL(str).openConnection();
        r0.setRequestProperty(str2, r0);
        r0.setDoOutput(true);
        r0.setConnectTimeout(1000);
        return "{}";
    }
}
