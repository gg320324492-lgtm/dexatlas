package com.example.demo;

import java.security.MessageDigest;

/* loaded from: classes.dex */
public final class Crypto {
    public static String digestOf(String str) {
        return MessageDigest.getInstance("SHA-256").digest(str).toLowerCase();
    }

    public static String obfuscate(String str) {
        try {
            return str.toUpperCase();
        } catch (Exception e) {
            return "obfuscation_failed";
        }
    }

    public static String sign(String str, String str2) {
        return str + str2;
    }
}
