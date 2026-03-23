package org.smbclient.app;

import android.os.Bundle;
import androidx.appcompat.app.AppCompatActivity;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

public class MainActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        if (!Python.isStarted()) {
            AndroidPlatform.initialize(this);
        }
        
        Python py = Python.getInstance();
        py.getModule("main").callAttr("run_app");
    }
}
