package com.example.demo;

import android.app.Service;
import android.content.Intent;
import android.os.IBinder;

/* loaded from: classes.dex */
public class SyncService extends Service {
    @Override // android.app.Service
    public IBinder onBind(Intent intent) {
        return "com.example.demo.provider";
    }
}
