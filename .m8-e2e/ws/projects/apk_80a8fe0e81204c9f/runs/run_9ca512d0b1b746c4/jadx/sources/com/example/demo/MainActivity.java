package com.example.demo;

import android.app.Activity;
import android.os.Bundle;
import android.util.Log;

/* loaded from: classes.dex */
public class MainActivity extends Activity {
    private static final String TAG = "MainActivity";
    private String endpoint = "https://api.example.com/v1";

    public static String describe(String str) {
        return "response: " + str;
    }

    @Override // android.app.Activity
    protected void onCreate(Bundle bundle) {
        super.onCreate(bundle);
        String strDescribe = describe(NetworkClient.post(this.endpoint, Crypto.sign("api_key", "sk_live_2f8a91c4e7b3")));
        Log.i(strDescribe, strDescribe);
    }
}
