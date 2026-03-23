package org.smbclient.app;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.view.GestureDetector;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ListView;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Stack;
import java.util.concurrent.ConcurrentHashMap;

public class MainActivity extends AppCompatActivity {

    private static final int PERMISSION_REQUEST_CODE = 100;
    private static final int SWIPE_THRESHOLD = 100;
    private static final int SWIPE_VELOCITY_THRESHOLD = 100;
    private static final int REQUEST_CODE_UPLOAD_FILE = 200;
    
    private Python py;
    private PyObject connectionManager;
    private PyObject fileBrowser;
    
    private LinearLayout mainLayout;
    private TextView tvStatus;
    private TextView tvPath;
    private TextView tvClipboard;
    private TextView tvTransferProgress;
    private ProgressBar progressBar;
    private ProgressBar progressBarTransfer;
    private LinearLayout layoutConnect;
    private LinearLayout layoutBrowser;
    private LinearLayout layoutShares;
    private LinearLayout layoutTransfer;
    private ListView lvFiles;
    private EditText etServerIp;
    private EditText etPort;
    private EditText etUsername;
    private EditText etPassword;
    private EditText etShareName;
    private Spinner spinnerConnections;
    private Button btnPaste;
    private Button btnBack;
    private Button btnForward;
    private Button btnHome;
    private Button btnUpload;
    private Button btnCancelTransfer;
    
    private List<Map<String, Object>> fileDataList = new ArrayList<>();
    private FileListAdapter fileAdapter;
    private Handler mainHandler = new Handler(Looper.getMainLooper());
    private JSONObject savedConnections;
    
    private GestureDetector gestureDetector;
    private Stack<String> backStack = new Stack<>();
    private Stack<String> forwardStack = new Stack<>();
    private String currentPath = "/";
    private boolean isViewingShares = false;
    private List<String> availableShares = new ArrayList<>();
    
    private boolean isTransferring = false;
    private volatile boolean cancelTransfer = false;
    private Map<String, TransferInfo> transferRecords = new ConcurrentHashMap<>();
    private static final String TRANSFER_RECORDS_FILE = "transfer_records.dat";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        if (!Python.isStarted()) {
            Python.start(new AndroidPlatform(this));
        }
        py = Python.getInstance();
        
        initPythonModules();
        loadTransferRecords();
        checkPermissions();
        setupUI();
        setupGestureDetector();
    }
    
    private void initPythonModules() {
        try {
            PyObject connectionModule = py.getModule("connection");
            connectionManager = connectionModule.callAttr("SMBConnectionManager");
            
            PyObject fileBrowserModule = py.getModule("file_browser");
            fileBrowser = fileBrowserModule.callAttr("FileBrowser");
            fileBrowser.callAttr("set_connection", connectionManager);
        } catch (Exception e) {
            String errorDetail = e.getMessage();
            if (e.getCause() != null) {
                errorDetail += "\n原因: " + e.getCause().getMessage();
            }
            showError("Python模块初始化失败:\n" + errorDetail);
        }
    }
    
    private void checkPermissions() {
        List<String> permissions = new ArrayList<>();
        
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.INTERNET) 
                != PackageManager.PERMISSION_GRANTED) {
            permissions.add(Manifest.permission.INTERNET);
        }
        
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_NETWORK_STATE) 
                != PackageManager.PERMISSION_GRANTED) {
            permissions.add(Manifest.permission.ACCESS_NETWORK_STATE);
        }
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            if (!Environment.isExternalStorageManager()) {
                try {
                    Intent intent = new Intent(android.provider.Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION);
                    intent.setData(android.net.Uri.parse("package:" + getPackageName()));
                    startActivityForResult(intent, PERMISSION_REQUEST_CODE);
                } catch (Exception e) {
                    Intent intent = new Intent(android.provider.Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION);
                    startActivityForResult(intent, PERMISSION_REQUEST_CODE);
                }
            }
        } else {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.WRITE_EXTERNAL_STORAGE) 
                    != PackageManager.PERMISSION_GRANTED) {
                permissions.add(Manifest.permission.WRITE_EXTERNAL_STORAGE);
            }
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.READ_EXTERNAL_STORAGE) 
                    != PackageManager.PERMISSION_GRANTED) {
                permissions.add(Manifest.permission.READ_EXTERNAL_STORAGE);
            }
        }
        
        if (!permissions.isEmpty()) {
            ActivityCompat.requestPermissions(this, 
                permissions.toArray(new String[0]), PERMISSION_REQUEST_CODE);
        }
    }
    
    private void setupGestureDetector() {
        gestureDetector = new GestureDetector(this, new GestureDetector.SimpleOnGestureListener() {
            @Override
            public boolean onFling(MotionEvent e1, MotionEvent e2, float velocityX, float velocityY) {
                if (e1 == null || e2 == null) return false;
                
                float diffX = e2.getX() - e1.getX();
                float diffY = e2.getY() - e1.getY();
                
                if (Math.abs(diffX) > Math.abs(diffY)) {
                    if (Math.abs(diffX) > SWIPE_THRESHOLD && Math.abs(velocityX) > SWIPE_VELOCITY_THRESHOLD) {
                        if (diffX > 0) {
                            onSwipeRight();
                        } else {
                            onSwipeLeft();
                        }
                        return true;
                    }
                }
                return false;
            }
        });
    }
    
    private void onSwipeRight() {
        if (layoutBrowser.getVisibility() == View.VISIBLE) {
            goBack();
        }
    }
    
    private void onSwipeLeft() {
        if (layoutBrowser.getVisibility() == View.VISIBLE) {
            goForward();
        }
    }
    
    @Override
    public boolean dispatchTouchEvent(MotionEvent ev) {
        gestureDetector.onTouchEvent(ev);
        return super.dispatchTouchEvent(ev);
    }
    
    private void setupUI() {
        mainLayout = new LinearLayout(this);
        mainLayout.setOrientation(LinearLayout.VERTICAL);
        mainLayout.setBackgroundColor(Color.parseColor("#FFFFFF"));
        mainLayout.setPadding(12, 12, 12, 12);
        
        tvStatus = new TextView(this);
        tvStatus.setText("未连接");
        tvStatus.setTextSize(14);
        tvStatus.setTextColor(Color.parseColor("#666666"));
        tvStatus.setPadding(0, 0, 0, 12);
        mainLayout.addView(tvStatus);
        
        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setVisibility(View.GONE);
        mainLayout.addView(progressBar);
        
        layoutConnect = new LinearLayout(this);
        layoutConnect.setOrientation(LinearLayout.VERTICAL);
        
        etServerIp = createEditText("服务器IP");
        layoutConnect.addView(etServerIp);
        
        etPort = createEditText("端口 (默认445)");
        etPort.setText("445");
        layoutConnect.addView(etPort);
        
        etUsername = createEditText("用户名");
        layoutConnect.addView(etUsername);
        
        etPassword = createEditText("密码");
        etPassword.setInputType(android.text.InputType.TYPE_CLASS_TEXT | 
            android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
        layoutConnect.addView(etPassword);
        
        etShareName = createEditText("共享名称 (可选)");
        layoutConnect.addView(etShareName);
        
        LinearLayout btnLayout = new LinearLayout(this);
        btnLayout.setOrientation(LinearLayout.HORIZONTAL);
        btnLayout.setPadding(0, 12, 0, 0);
        
        Button btnConnect = createButton("连接");
        btnConnect.setOnClickListener(v -> connect());
        btnLayout.addView(btnConnect);
        
        Button btnSaveConn = createButton("保存");
        btnSaveConn.setOnClickListener(v -> saveConnection());
        btnLayout.addView(btnSaveConn);
        
        Button btnLoadConn = createButton("加载");
        btnLoadConn.setOnClickListener(v -> loadConnections());
        btnLayout.addView(btnLoadConn);
        
        Button btnDeleteConn = createButton("删除");
        btnDeleteConn.setOnClickListener(v -> deleteConnection());
        btnLayout.addView(btnDeleteConn);
        
        layoutConnect.addView(btnLayout);
        
        spinnerConnections = new Spinner(this);
        layoutConnect.addView(spinnerConnections);
        
        mainLayout.addView(layoutConnect);
        
        layoutBrowser = new LinearLayout(this);
        layoutBrowser.setOrientation(LinearLayout.VERTICAL);
        layoutBrowser.setVisibility(View.GONE);
        
        TextView tvPathLabel = new TextView(this);
        tvPathLabel.setText("当前路径:");
        tvPathLabel.setTextSize(12);
        tvPathLabel.setTextColor(Color.parseColor("#999999"));
        layoutBrowser.addView(tvPathLabel);
        
        tvPath = new TextView(this);
        tvPath.setText("/");
        tvPath.setTextSize(14);
        tvPath.setTextColor(Color.parseColor("#333333"));
        tvPath.setTypeface(null, Typeface.BOLD);
        tvPath.setPadding(0, 0, 0, 8);
        layoutBrowser.addView(tvPath);
        
        LinearLayout navBtnLayout = new LinearLayout(this);
        navBtnLayout.setOrientation(LinearLayout.HORIZONTAL);
        
        btnBack = createButton("◀");
        btnBack.setOnClickListener(v -> goBack());
        btnBack.setEnabled(false);
        navBtnLayout.addView(btnBack);
        
        btnForward = createButton("▶");
        btnForward.setOnClickListener(v -> goForward());
        btnForward.setEnabled(false);
        navBtnLayout.addView(btnForward);
        
        btnHome = createButton("主页");
        btnHome.setOnClickListener(v -> goHome());
        navBtnLayout.addView(btnHome);
        
        layoutBrowser.addView(navBtnLayout);
        
        LinearLayout actionBtnLayout = new LinearLayout(this);
        actionBtnLayout.setOrientation(LinearLayout.HORIZONTAL);
        
        Button btnUp = createButton("上级");
        btnUp.setOnClickListener(v -> navigateUp());
        actionBtnLayout.addView(btnUp);
        
        Button btnRefresh = createButton("刷新");
        btnRefresh.setOnClickListener(v -> refreshFileList());
        actionBtnLayout.addView(btnRefresh);
        
        Button btnNewDir = createButton("新建");
        btnNewDir.setOnClickListener(v -> showCreateDirectoryDialog());
        actionBtnLayout.addView(btnNewDir);
        
        btnUpload = createButton("上传");
        btnUpload.setOnClickListener(v -> selectFileToUpload());
        actionBtnLayout.addView(btnUpload);
        
        btnPaste = createButton("粘贴");
        btnPaste.setOnClickListener(v -> pasteFromClipboard());
        btnPaste.setEnabled(false);
        actionBtnLayout.addView(btnPaste);
        
        Button btnDisconnect = createButton("断开");
        btnDisconnect.setOnClickListener(v -> disconnect());
        actionBtnLayout.addView(btnDisconnect);
        
        layoutBrowser.addView(actionBtnLayout);
        
        tvClipboard = new TextView(this);
        tvClipboard.setTextSize(12);
        tvClipboard.setTextColor(Color.parseColor("#FF9800"));
        tvClipboard.setPadding(0, 8, 0, 4);
        tvClipboard.setVisibility(View.GONE);
        layoutBrowser.addView(tvClipboard);
        
        layoutTransfer = new LinearLayout(this);
        layoutTransfer.setOrientation(LinearLayout.VERTICAL);
        layoutTransfer.setVisibility(View.GONE);
        layoutTransfer.setBackgroundColor(Color.parseColor("#F5F5F5"));
        layoutTransfer.setPadding(8, 8, 8, 8);
        
        tvTransferProgress = new TextView(this);
        tvTransferProgress.setText("准备中...");
        tvTransferProgress.setTextSize(12);
        tvTransferProgress.setTextColor(Color.parseColor("#666666"));
        layoutTransfer.addView(tvTransferProgress);
        
        progressBarTransfer = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBarTransfer.setMax(100);
        progressBarTransfer.setProgress(0);
        layoutTransfer.addView(progressBarTransfer);
        
        btnCancelTransfer = createButton("取消");
        btnCancelTransfer.setOnClickListener(v -> cancelCurrentTransfer());
        layoutTransfer.addView(btnCancelTransfer);
        
        layoutBrowser.addView(layoutTransfer);
        
        TextView tvFilesLabel = new TextView(this);
        tvFilesLabel.setText("文件列表:");
        tvFilesLabel.setTextSize(12);
        tvFilesLabel.setTextColor(Color.parseColor("#999999"));
        tvFilesLabel.setPadding(0, 8, 0, 4);
        layoutBrowser.addView(tvFilesLabel);
        
        lvFiles = new ListView(this);
        fileAdapter = new FileListAdapter(this, fileDataList);
        lvFiles.setAdapter(fileAdapter);
        lvFiles.setOnItemClickListener((parent, view, position, id) -> {
            onFileClick(position);
        });
        lvFiles.setOnItemLongClickListener((parent, view, position, id) -> {
            showFileOperationDialog(position);
            return true;
        });
        
        LinearLayout.LayoutParams lvParams = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, 
            LinearLayout.LayoutParams.MATCH_PARENT, 
            1.0f);
        layoutBrowser.addView(lvFiles, lvParams);
        
        mainLayout.addView(layoutBrowser);
        
        layoutShares = new LinearLayout(this);
        layoutShares.setOrientation(LinearLayout.VERTICAL);
        layoutShares.setVisibility(View.GONE);
        
        TextView tvSharesTitle = new TextView(this);
        tvSharesTitle.setText("可用共享列表:");
        tvSharesTitle.setTextSize(14);
        tvSharesTitle.setTextColor(Color.parseColor("#333333"));
        tvSharesTitle.setTypeface(null, Typeface.BOLD);
        tvSharesTitle.setPadding(0, 12, 0, 8);
        layoutShares.addView(tvSharesTitle);
        
        ListView lvShares = new ListView(this);
        ArrayAdapter<String> sharesAdapter = new ArrayAdapter<>(this,
            android.R.layout.simple_list_item_1, availableShares);
        lvShares.setAdapter(sharesAdapter);
        lvShares.setOnItemClickListener((parent, view, position, id) -> {
            String shareName = availableShares.get(position);
            selectShare(shareName);
        });
        
        LinearLayout.LayoutParams sharesLvParams = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.MATCH_PARENT,
            1.0f);
        layoutShares.addView(lvShares, sharesLvParams);
        
        Button btnSharesDisconnect = createButton("断开连接");
        btnSharesDisconnect.setOnClickListener(v -> disconnect());
        layoutShares.addView(btnSharesDisconnect);
        
        mainLayout.addView(layoutShares);
        
        setContentView(mainLayout);
    }
    
    private EditText createEditText(String hint) {
        EditText et = new EditText(this);
        et.setHint(hint);
        et.setTextSize(14);
        et.setBackgroundColor(Color.parseColor("#F5F5F5"));
        et.setPadding(12, 12, 12, 12);
        return et;
    }
    
    private Button createButton(String text) {
        Button btn = new Button(this);
        btn.setText(text);
        btn.setAllCaps(false);
        btn.setTextSize(13);
        return btn;
    }
    
    private void connect() {
        String serverIp = etServerIp.getText().toString().trim();
        String port = etPort.getText().toString().trim();
        String username = etUsername.getText().toString().trim();
        String password = etPassword.getText().toString().trim();
        String shareName = etShareName.getText().toString().trim();
        
        if (serverIp.isEmpty()) {
            showError("请输入服务器IP");
            return;
        }
        
        showProgress(true);
        tvStatus.setText("正在连接...");
        
        new Thread(() -> {
            try {
                String resultJson = connectionManager.callAttr("connect",
                    serverIp, port, username, password, shareName).toString();
                JSONArray resultArray = new JSONArray(resultJson);
                
                boolean success = resultArray.getBoolean(0);
                String message = resultArray.getString(1);
                
                mainHandler.post(() -> {
                    showProgress(false);
                    tvStatus.setText(message);
                    
                    if (success) {
                        layoutConnect.setVisibility(View.GONE);
                        
                        if (shareName.isEmpty()) {
                            showSharesList();
                        } else {
                            layoutBrowser.setVisibility(View.VISIBLE);
                            layoutShares.setVisibility(View.GONE);
                            clearNavigationHistory();
                            loadPath("/");
                        }
                    } else {
                        showError(message);
                    }
                });
            } catch (Exception e) {
                mainHandler.post(() -> {
                    showProgress(false);
                    showError("连接失败: " + e.getMessage());
                });
            }
        }).start();
    }
    
    private void showSharesList() {
        try {
            availableShares.clear();
            String sharesJson = connectionManager.callAttr("get_available_shares_json").toString();
            JSONArray sharesArray = new JSONArray(sharesJson);
            
            for (int i = 0; i < sharesArray.length(); i++) {
                availableShares.add(sharesArray.getString(i));
            }
            
            isViewingShares = true;
            layoutBrowser.setVisibility(View.GONE);
            layoutShares.setVisibility(View.VISIBLE);
            
            ListView lvShares = (ListView) layoutShares.getChildAt(1);
            ArrayAdapter<String> adapter = new ArrayAdapter<>(this,
                android.R.layout.simple_list_item_1, availableShares);
            lvShares.setAdapter(adapter);
            
        } catch (Exception e) {
            showError("获取共享列表失败: " + e.getMessage());
        }
    }
    
    private void selectShare(String shareName) {
        connectionManager.callAttr("set_current_share", shareName);
        isViewingShares = false;
        layoutShares.setVisibility(View.GONE);
        layoutBrowser.setVisibility(View.VISIBLE);
        clearNavigationHistory();
        loadPath("/");
    }
    
    private void clearNavigationHistory() {
        backStack.clear();
        forwardStack.clear();
        updateNavigationButtons();
    }
    
    private void updateNavigationButtons() {
        btnBack.setEnabled(!backStack.isEmpty());
        btnForward.setEnabled(!forwardStack.isEmpty());
    }
    
    private void goBack() {
        if (backStack.isEmpty()) {
            Toast.makeText(this, "没有后退历史", Toast.LENGTH_SHORT).show();
            return;
        }
        
        forwardStack.push(currentPath);
        String previousPath = backStack.pop();
        loadPathWithoutHistory(previousPath);
        updateNavigationButtons();
    }
    
    private void goForward() {
        if (forwardStack.isEmpty()) {
            Toast.makeText(this, "没有前进历史", Toast.LENGTH_SHORT).show();
            return;
        }
        
        backStack.push(currentPath);
        String nextPath = forwardStack.pop();
        loadPathWithoutHistory(nextPath);
        updateNavigationButtons();
    }
    
    private void goHome() {
        if (isViewingShares) {
            return;
        }
        
        backStack.push(currentPath);
        forwardStack.clear();
        showSharesList();
        updateNavigationButtons();
    }
    
    private void loadPathWithoutHistory(String path) {
        showProgress(true);
        currentPath = path;
        
        new Thread(() -> {
            try {
                fileBrowser.callAttr("load_path", path);
                String filesJson = fileBrowser.callAttr("get_current_files_json").toString();
                JSONArray jsonArray = new JSONArray(filesJson);
                
                final List<Map<String, Object>> newFileList = new ArrayList<>();
                for (int i = 0; i < jsonArray.length(); i++) {
                    JSONObject fileObj = jsonArray.getJSONObject(i);
                    Map<String, Object> fileData = new HashMap<>();
                    fileData.put("filename", fileObj.optString("filename", ""));
                    fileData.put("isDirectory", fileObj.optBoolean("isDirectory", false));
                    fileData.put("file_size_str", fileObj.optString("file_size_str", ""));
                    fileData.put("last_write_time_str", fileObj.optString("last_write_time_str", ""));
                    newFileList.add(fileData);
                }
                
                mainHandler.post(() -> {
                    showProgress(false);
                    fileAdapter.updateData(newFileList);
                    tvPath.setText(path);
                    updateClipboardUI();
                });
            } catch (Exception e) {
                mainHandler.post(() -> {
                    showProgress(false);
                    showError("加载目录失败: " + e.getMessage());
                });
            }
        }).start();
    }
    
    private void saveConnection() {
        String serverIp = etServerIp.getText().toString().trim();
        String port = etPort.getText().toString().trim();
        String username = etUsername.getText().toString().trim();
        String password = etPassword.getText().toString().trim();
        String shareName = etShareName.getText().toString().trim();
        
        if (serverIp.isEmpty()) {
            showError("请输入服务器IP");
            return;
        }
        
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("保存连接");
        
        final EditText input = new EditText(this);
        input.setHint("连接名称");
        builder.setView(input);
        
        builder.setPositiveButton("保存", (dialog, which) -> {
            String name = input.getText().toString().trim();
            if (name.isEmpty()) {
                Toast.makeText(this, "请输入连接名称", Toast.LENGTH_SHORT).show();
                return;
            }
            
            try {
                Map<String, Object> connData = new HashMap<>();
                connData.put("name", name);
                connData.put("server_ip", serverIp);
                connData.put("port", port);
                connData.put("username", username);
                connData.put("password", password);
                connData.put("share_name", shareName);
                
                PyObject pyDict = py.getBuiltins().callAttr("dict");
                for (Map.Entry<String, Object> entry : connData.entrySet()) {
                    pyDict.callAttr("__setitem__", entry.getKey(), entry.getValue());
                }
                
                connectionManager.callAttr("save_connection", pyDict);
                Toast.makeText(this, "连接已保存: " + name, Toast.LENGTH_SHORT).show();
                loadConnections();
            } catch (Exception e) {
                showError("保存失败: " + e.getMessage());
            }
        });
        builder.setNegativeButton("取消", null);
        builder.show();
    }
    
    private void deleteConnection() {
        if (savedConnections == null || savedConnections.length() == 0) {
            Toast.makeText(this, "没有保存的连接", Toast.LENGTH_SHORT).show();
            return;
        }
        
        List<String> connList = new ArrayList<>();
        java.util.Iterator<String> keys = savedConnections.keys();
        while (keys.hasNext()) {
            connList.add(keys.next());
        }
        
        String[] connArray = connList.toArray(new String[0]);
        
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("选择要删除的连接");
        builder.setItems(connArray, (dialog, which) -> {
            String connName = connArray[which];
            new AlertDialog.Builder(this)
                .setTitle("确认删除")
                .setMessage("确定要删除连接 \"" + connName + "\" 吗？")
                .setPositiveButton("删除", (d, w) -> {
                    performDeleteConnection(connName);
                })
                .setNegativeButton("取消", null)
                .show();
        });
        builder.setNegativeButton("取消", null);
        builder.show();
    }
    
    private void performDeleteConnection(String name) {
        new Thread(() -> {
            try {
                String resultJson = connectionManager.callAttr("delete_connection", name).toString();
                JSONArray resultArray = new JSONArray(resultJson);
                boolean success = resultArray.getBoolean(0);
                String message = resultArray.getString(1);
                
                mainHandler.post(() -> {
                    Toast.makeText(this, message, Toast.LENGTH_SHORT).show();
                    if (success) {
                        loadConnections();
                    }
                });
            } catch (Exception e) {
                mainHandler.post(() -> showError("删除失败: " + e.getMessage()));
            }
        }).start();
    }
    
    private void disconnect() {
        connectionManager.callAttr("disconnect");
        layoutConnect.setVisibility(View.VISIBLE);
        layoutBrowser.setVisibility(View.GONE);
        layoutShares.setVisibility(View.GONE);
        tvStatus.setText("未连接");
        fileDataList.clear();
        fileAdapter.notifyDataSetChanged();
        fileBrowser.callAttr("clear_clipboard");
        updateClipboardUI();
        clearNavigationHistory();
        isViewingShares = false;
    }
    
    private void loadPath(String path) {
        if (!currentPath.equals(path)) {
            backStack.push(currentPath);
            forwardStack.clear();
            currentPath = path;
            updateNavigationButtons();
        }
        
        loadPathWithoutHistory(path);
    }
    
    private void navigateUp() {
        new Thread(() -> {
            try {
                fileBrowser.callAttr("navigate_up");
                String newPath = fileBrowser.callAttr("get_current_path").toString();
                mainHandler.post(() -> loadPath(newPath));
            } catch (Exception e) {
                mainHandler.post(() -> showError("返回上级失败: " + e.getMessage()));
            }
        }).start();
    }
    
    private void refreshFileList() {
        loadPathWithoutHistory(currentPath);
    }
    
    private void onFileClick(int position) {
        if (position < 0 || position >= fileDataList.size()) {
            return;
        }
        
        Map<String, Object> fileData = fileDataList.get(position);
        String filename = (String) fileData.get("filename");
        boolean isDir = (Boolean) fileData.get("isDirectory");
        
        if (isDir) {
            String newPath;
            if (currentPath.equals("/")) {
                newPath = "/" + filename;
            } else {
                newPath = currentPath + "/" + filename;
            }
            loadPath(newPath);
        } else {
            showFileOperationDialog(position);
        }
    }
    
    private void showFileOperationDialog(int position) {
        if (position < 0 || position >= fileDataList.size()) {
            return;
        }
        
        Map<String, Object> fileData = fileDataList.get(position);
        String filename = (String) fileData.get("filename");
        boolean isDir = (Boolean) fileData.get("isDirectory");
        
        String[] options;
        if (isDir) {
            options = new String[]{"打开", "重命名", "复制", "剪切", "删除"};
        } else {
            options = new String[]{"打开/下载", "断点续传下载", "重命名", "复制", "剪切", "删除"};
        }
        
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle((isDir ? "📁 " : "📄 ") + filename);
        builder.setItems(options, (dialog, which) -> {
            if (isDir) {
                switch (which) {
                    case 0: onFileClick(position); break;
                    case 1: showRenameDialog(filename); break;
                    case 2: copyToClipboard(filename, isDir); break;
                    case 3: cutToClipboard(filename, isDir); break;
                    case 4: showDeleteConfirmDialog(filename, isDir); break;
                }
            } else {
                switch (which) {
                    case 0: downloadAndOpenFile(filename); break;
                    case 1: downloadWithResume(filename); break;
                    case 2: showRenameDialog(filename); break;
                    case 3: copyToClipboard(filename, isDir); break;
                    case 4: cutToClipboard(filename, isDir); break;
                    case 5: showDeleteConfirmDialog(filename, isDir); break;
                }
            }
        });
        builder.show();
    }
    
    private void selectFileToUpload() {
        Intent intent = new Intent(Intent.ACTION_GET_CONTENT);
        intent.setType("*/*");
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        startActivityForResult(intent, REQUEST_CODE_UPLOAD_FILE);
    }
    
    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        
        if (requestCode == REQUEST_CODE_UPLOAD_FILE && resultCode == RESULT_OK && data != null) {
            Uri uri = data.getData();
            if (uri != null) {
                uploadFile(uri);
            }
        }
    }
    
    private void uploadFile(Uri uri) {
        try {
            String fileName = getFileNameFromUri(uri);
            showTransferUI(true, "上传: " + fileName);
            
            new Thread(() -> {
                try {
                    java.io.InputStream inputStream = getContentResolver().openInputStream(uri);
                    if (inputStream == null) {
                        mainHandler.post(() -> {
                            hideTransferUI();
                            showError("无法读取文件");
                        });
                        return;
                    }
                    
                    String tempPath = getCacheDir().getAbsolutePath() + "/upload_temp_" + fileName;
                    java.io.File tempFile = new java.io.File(tempPath);
                    
                    java.io.FileOutputStream fos = new java.io.FileOutputStream(tempFile);
                    byte[] buffer = new byte[8192];
                    int bytesRead;
                    
                    while ((bytesRead = inputStream.read(buffer)) != -1) {
                        if (cancelTransfer) {
                            inputStream.close();
                            fos.close();
                            tempFile.delete();
                            mainHandler.post(() -> {
                                hideTransferUI();
                                Toast.makeText(this, "上传已取消", Toast.LENGTH_SHORT).show();
                            });
                            return;
                        }
                        fos.write(buffer, 0, bytesRead);
                    }
                    
                    inputStream.close();
                    fos.close();
                    
                    String resultJson = fileBrowser.callAttr("upload_file", fileName, tempPath).toString();
                    JSONArray resultArray = new JSONArray(resultJson);
                    boolean success = resultArray.getBoolean(0);
                    String message = resultArray.getString(1);
                    
                    tempFile.delete();
                    
                    mainHandler.post(() -> {
                        hideTransferUI();
                        if (success) {
                            Toast.makeText(this, message, Toast.LENGTH_SHORT).show();
                            refreshFileList();
                        } else {
                            showError(message);
                        }
                    });
                    
                } catch (Exception e) {
                    mainHandler.post(() -> {
                        hideTransferUI();
                        showError("上传失败: " + e.getMessage());
                    });
                }
            }).start();
            
        } catch (Exception e) {
            showError("上传失败: " + e.getMessage());
        }
    }
    
    private String getFileNameFromUri(Uri uri) {
        String fileName = "upload_file";
        String scheme = uri.getScheme();
        
        if (scheme != null && scheme.equals("content")) {
            android.database.Cursor cursor = getContentResolver().query(uri, null, null, null, null);
            if (cursor != null && cursor.moveToFirst()) {
                int nameIndex = cursor.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME);
                if (nameIndex >= 0) {
                    fileName = cursor.getString(nameIndex);
                }
                cursor.close();
            }
        } else if (scheme != null && scheme.equals("file")) {
            fileName = new java.io.File(uri.getPath()).getName();
        }
        
        return fileName;
    }
    
    private void downloadAndOpenFile(String filename) {
        showTransferUI(true, "下载: " + filename);
        
        new Thread(() -> {
            try {
                java.io.File cacheDir = new java.io.File(getCacheDir(), "downloads");
                if (!cacheDir.exists()) {
                    cacheDir.mkdirs();
                }
                
                String localPath = cacheDir.getAbsolutePath() + "/" + filename;
                String resultJson = fileBrowser.callAttr("download_file", filename, cacheDir.getAbsolutePath()).toString();
                JSONArray resultArray = new JSONArray(resultJson);
                
                boolean success = resultArray.getBoolean(0);
                String message = resultArray.getString(1);
                
                mainHandler.post(() -> {
                    hideTransferUI();
                    
                    if (success) {
                        openFileWithSystemApp(localPath, filename);
                    } else {
                        showError(message);
                    }
                });
            } catch (Exception e) {
                mainHandler.post(() -> {
                    hideTransferUI();
                    showError("下载失败: " + e.getMessage());
                });
            }
        }).start();
    }
    
    private void downloadWithResume(String filename) {
        String transferKey = connectionManager.callAttr("current_server_ip").toString() + "_" + 
                            connectionManager.callAttr("current_share").toString() + "_" + 
                            currentPath + "/" + filename;
        
        TransferInfo info = transferRecords.get(transferKey);
        
        if (info != null) {
            new AlertDialog.Builder(this)
                .setTitle("断点续传")
                .setMessage("发现未完成的下载记录，已下载 " + formatSize(info.transferredBytes) + "。\n是否继续下载？")
                .setPositiveButton("继续", (d, w) -> resumeDownload(filename, transferKey, info))
                .setNegativeButton("重新下载", (d, w) -> startNewDownload(filename, transferKey))
                .setNeutralButton("取消", null)
                .show();
        } else {
            startNewDownload(filename, transferKey);
        }
    }
    
    private void startNewDownload(String filename, String transferKey) {
        TransferInfo info = new TransferInfo();
        info.remotePath = currentPath.equals("/") ? "/" + filename : currentPath + "/" + filename;
        info.localPath = getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS).getAbsolutePath() + "/" + filename;
        info.transferredBytes = 0;
        info.totalBytes = 0;
        info.isDownload = true;
        
        transferRecords.put(transferKey, info);
        saveTransferRecords();
        
        performDownload(filename, transferKey, info);
    }
    
    private void resumeDownload(String filename, String transferKey, TransferInfo info) {
        performDownload(filename, transferKey, info);
    }
    
    private void performDownload(String filename, String transferKey, TransferInfo info) {
        showTransferUI(true, "下载: " + filename);
        isTransferring = true;
        cancelTransfer = false;
        
        new Thread(() -> {
            try {
                String resultJson = fileBrowser.callAttr("download_file_resume", 
                    filename, 
                    info.localPath, 
                    info.transferredBytes).toString();
                
                JSONObject result = new JSONObject(resultJson);
                boolean success = result.getBoolean("success");
                String message = result.getString("message");
                long totalBytes = result.optLong("total_bytes", 0);
                long transferredBytes = result.optLong("transferred_bytes", 0);
                
                if (success) {
                    transferRecords.remove(transferKey);
                    saveTransferRecords();
                    
                    mainHandler.post(() -> {
                        hideTransferUI();
                        Toast.makeText(this, "下载完成: " + filename, Toast.LENGTH_SHORT).show();
                    });
                } else if (cancelTransfer) {
                    info.transferredBytes = transferredBytes;
                    info.totalBytes = totalBytes;
                    transferRecords.put(transferKey, info);
                    saveTransferRecords();
                    
                    mainHandler.post(() -> {
                        hideTransferUI();
                        Toast.makeText(this, "下载已暂停，可稍后继续", Toast.LENGTH_SHORT).show();
                    });
                } else {
                    mainHandler.post(() -> {
                        hideTransferUI();
                        showError(message);
                    });
                }
                
            } catch (Exception e) {
                mainHandler.post(() -> {
                    hideTransferUI();
                    showError("下载失败: " + e.getMessage());
                });
            }
            
            isTransferring = false;
        }).start();
    }
    
    private void cancelCurrentTransfer() {
        cancelTransfer = true;
    }
    
    private void showTransferUI(boolean show, String message) {
        layoutTransfer.setVisibility(show ? View.VISIBLE : View.GONE);
        tvTransferProgress.setText(message);
        progressBarTransfer.setProgress(0);
    }
    
    private void hideTransferUI() {
        layoutTransfer.setVisibility(View.GONE);
        isTransferring = false;
        cancelTransfer = false;
    }
    
    private String formatSize(long bytes) {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return String.format("%.1f KB", bytes / 1024.0);
        if (bytes < 1024 * 1024 * 1024) return String.format("%.1f MB", bytes / (1024.0 * 1024));
        return String.format("%.1f GB", bytes / (1024.0 * 1024 * 1024));
    }
    
    private void openFileWithSystemApp(String filePath, String filename) {
        try {
            java.io.File file = new java.io.File(filePath);
            if (!file.exists()) {
                showError("文件不存在: " + filePath);
                return;
            }
            
            android.net.Uri uri;
            Intent intent = new Intent(Intent.ACTION_VIEW);
            
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                uri = androidx.core.content.FileProvider.getUriForFile(
                    this,
                    getPackageName() + ".fileprovider",
                    file
                );
                intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            } else {
                uri = android.net.Uri.fromFile(file);
            }
            
            String mimeType = getMimeType(filename);
            intent.setDataAndType(uri, mimeType);
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            
            try {
                startActivity(intent);
            } catch (android.content.ActivityNotFoundException e) {
                showError("没有应用可以打开此文件类型: " + mimeType);
            }
        } catch (Exception e) {
            showError("打开文件失败: " + e.getMessage());
        }
    }
    
    private String getMimeType(String filename) {
        String extension = filename.substring(filename.lastIndexOf(".") + 1).toLowerCase();
        
        switch (extension) {
            case "txt": return "text/plain";
            case "pdf": return "application/pdf";
            case "doc": return "application/msword";
            case "docx": return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
            case "xls": return "application/vnd.ms-excel";
            case "xlsx": return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
            case "ppt": return "application/vnd.ms-powerpoint";
            case "pptx": return "application/vnd.openxmlformats-officedocument.presentationml.presentation";
            case "jpg":
            case "jpeg": return "image/jpeg";
            case "png": return "image/png";
            case "gif": return "image/gif";
            case "bmp": return "image/bmp";
            case "webp": return "image/webp";
            case "mp3": return "audio/mpeg";
            case "mp4": return "video/mp4";
            case "avi": return "video/x-msvideo";
            case "mkv": return "video/x-matroska";
            case "zip": return "application/zip";
            case "rar": return "application/x-rar-compressed";
            case "7z": return "application/x-7z-compressed";
            case "html":
            case "htm": return "text/html";
            case "xml": return "application/xml";
            case "json": return "application/json";
            case "csv": return "text/csv";
            default: return "application/octet-stream";
        }
    }
    
    private void showCreateDirectoryDialog() {
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("新建目录");
        
        final EditText input = new EditText(this);
        input.setHint("目录名称");
        builder.setView(input);
        
        builder.setPositiveButton("创建", (dialog, which) -> {
            String dirName = input.getText().toString().trim();
            if (dirName.isEmpty()) {
                Toast.makeText(this, "请输入目录名称", Toast.LENGTH_SHORT).show();
                return;
            }
            createDirectory(dirName);
        });
        builder.setNegativeButton("取消", null);
        builder.show();
    }
    
    private void createDirectory(String dirName) {
        new Thread(() -> {
            try {
                String resultJson = fileBrowser.callAttr("create_directory", dirName).toString();
                JSONArray resultArray = new JSONArray(resultJson);
                boolean success = resultArray.getBoolean(0);
                String message = resultArray.getString(1);
                
                mainHandler.post(() -> {
                    Toast.makeText(this, message, Toast.LENGTH_SHORT).show();
                    if (success) {
                        refreshFileList();
                    }
                });
            } catch (Exception e) {
                mainHandler.post(() -> showError("创建目录失败: " + e.getMessage()));
            }
        }).start();
    }
    
    private void showRenameDialog(String oldName) {
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("重命名");
        
        final EditText input = new EditText(this);
        input.setText(oldName);
        input.selectAll();
        builder.setView(input);
        
        builder.setPositiveButton("确定", (dialog, which) -> {
            String newName = input.getText().toString().trim();
            if (newName.isEmpty() || newName.equals(oldName)) {
                return;
            }
            renameItem(oldName, newName);
        });
        builder.setNegativeButton("取消", null);
        builder.show();
    }
    
    private void renameItem(String oldName, String newName) {
        new Thread(() -> {
            try {
                String resultJson = fileBrowser.callAttr("rename_item", oldName, newName).toString();
                JSONArray resultArray = new JSONArray(resultJson);
                boolean success = resultArray.getBoolean(0);
                String message = resultArray.getString(1);
                
                mainHandler.post(() -> {
                    Toast.makeText(this, message, Toast.LENGTH_SHORT).show();
                    if (success) {
                        refreshFileList();
                    }
                });
            } catch (Exception e) {
                mainHandler.post(() -> showError("重命名失败: " + e.getMessage()));
            }
        }).start();
    }
    
    private void showDeleteConfirmDialog(String filename, boolean isDir) {
        String type = isDir ? "目录" : "文件";
        new AlertDialog.Builder(this)
            .setTitle("确认删除")
            .setMessage("确定要删除" + type + " \"" + filename + "\" 吗？")
            .setPositiveButton("删除", (dialog, which) -> deleteItem(filename, isDir))
            .setNegativeButton("取消", null)
            .show();
    }
    
    private void deleteItem(String filename, boolean isDir) {
        new Thread(() -> {
            try {
                String resultJson = fileBrowser.callAttr("delete_item", filename, isDir).toString();
                JSONArray resultArray = new JSONArray(resultJson);
                boolean success = resultArray.getBoolean(0);
                String message = resultArray.getString(1);
                
                mainHandler.post(() -> {
                    Toast.makeText(this, message, Toast.LENGTH_SHORT).show();
                    if (success) {
                        refreshFileList();
                    }
                });
            } catch (Exception e) {
                mainHandler.post(() -> showError("删除失败: " + e.getMessage()));
            }
        }).start();
    }
    
    private void copyToClipboard(String filename, boolean isDir) {
        try {
            String resultJson = fileBrowser.callAttr("copy_to_clipboard", filename, isDir).toString();
            JSONArray resultArray = new JSONArray(resultJson);
            boolean success = resultArray.getBoolean(0);
            String message = resultArray.getString(1);
            
            Toast.makeText(this, message, Toast.LENGTH_SHORT).show();
            updateClipboardUI();
        } catch (Exception e) {
            showError("复制失败: " + e.getMessage());
        }
    }
    
    private void cutToClipboard(String filename, boolean isDir) {
        try {
            String resultJson = fileBrowser.callAttr("cut_to_clipboard", filename, isDir).toString();
            JSONArray resultArray = new JSONArray(resultJson);
            boolean success = resultArray.getBoolean(0);
            String message = resultArray.getString(1);
            
            Toast.makeText(this, message, Toast.LENGTH_SHORT).show();
            updateClipboardUI();
        } catch (Exception e) {
            showError("剪切失败: " + e.getMessage());
        }
    }
    
    private void pasteFromClipboard() {
        new Thread(() -> {
            try {
                String resultJson = fileBrowser.callAttr("paste_from_clipboard").toString();
                JSONArray resultArray = new JSONArray(resultJson);
                boolean success = resultArray.getBoolean(0);
                String message = resultArray.getString(1);
                
                mainHandler.post(() -> {
                    Toast.makeText(this, message, Toast.LENGTH_SHORT).show();
                    if (success) {
                        refreshFileList();
                    }
                });
            } catch (Exception e) {
                mainHandler.post(() -> showError("粘贴失败: " + e.getMessage()));
            }
        }).start();
    }
    
    private void updateClipboardUI() {
        try {
            boolean hasClipboard = fileBrowser.callAttr("has_clipboard").toBoolean();
            btnPaste.setEnabled(hasClipboard);
            
            if (hasClipboard) {
                String clipboardInfo = fileBrowser.callAttr("get_clipboard_info").toString();
                JSONObject info = new JSONObject(clipboardInfo);
                String operation = info.optString("operation", "");
                String filename = info.optString("filename", "");
                String opText = "copy".equals(operation) ? "复制" : "剪切";
                tvClipboard.setText("剪贴板: " + opText + " - " + filename);
                tvClipboard.setVisibility(View.VISIBLE);
            } else {
                tvClipboard.setVisibility(View.GONE);
            }
        } catch (Exception e) {
            btnPaste.setEnabled(false);
            tvClipboard.setVisibility(View.GONE);
        }
    }
    
    private void loadConnections() {
        try {
            String connectionsJson = connectionManager.callAttr("get_all_connections_json").toString();
            savedConnections = new JSONObject(connectionsJson);
            
            List<String> connList = new ArrayList<>();
            java.util.Iterator<String> keys = savedConnections.keys();
            while (keys.hasNext()) {
                connList.add(keys.next());
            }
            
            if (connList.isEmpty()) {
                Toast.makeText(this, "没有保存的连接", Toast.LENGTH_SHORT).show();
                return;
            }
            
            ArrayAdapter<String> adapter = new ArrayAdapter<>(this,
                android.R.layout.simple_spinner_item, connList);
            adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
            spinnerConnections.setAdapter(adapter);
            
            spinnerConnections.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
                @Override
                public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                    String connName = connList.get(position);
                    try {
                        JSONObject connData = savedConnections.getJSONObject(connName);
                        
                        etServerIp.setText(connData.optString("server_ip", ""));
                        etPort.setText(connData.optString("port", "445"));
                        etUsername.setText(connData.optString("username", ""));
                        etPassword.setText(connData.optString("password", ""));
                        etShareName.setText(connData.optString("share_name", ""));
                    } catch (Exception e) {
                        System.out.println("加载连接数据失败: " + e.getMessage());
                    }
                }
                
                @Override
                public void onNothingSelected(AdapterView<?> parent) {}
            });
            
        } catch (Exception e) {
            showError("加载连接失败: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    private void showProgress(boolean show) {
        progressBar.setVisibility(show ? View.VISIBLE : View.GONE);
    }
    
    private void showError(String message) {
        new AlertDialog.Builder(this)
            .setTitle("错误")
            .setMessage(message)
            .setPositiveButton("确定", null)
            .show();
    }
    
    @SuppressWarnings("unchecked")
    private void loadTransferRecords() {
        try {
            File file = new File(getFilesDir(), TRANSFER_RECORDS_FILE);
            if (file.exists()) {
                ObjectInputStream ois = new ObjectInputStream(new FileInputStream(file));
                transferRecords = (Map<String, TransferInfo>) ois.readObject();
                ois.close();
            }
        } catch (Exception e) {
            transferRecords = new ConcurrentHashMap<>();
        }
    }
    
    private void saveTransferRecords() {
        try {
            File file = new File(getFilesDir(), TRANSFER_RECORDS_FILE);
            ObjectOutputStream oos = new ObjectOutputStream(new FileOutputStream(file));
            oos.writeObject(transferRecords);
            oos.close();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
    
    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, 
            @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == PERMISSION_REQUEST_CODE) {
            for (int result : grantResults) {
                if (result != PackageManager.PERMISSION_GRANTED) {
                    Toast.makeText(this, "部分权限被拒绝，功能可能受限", Toast.LENGTH_LONG).show();
                    break;
                }
            }
        }
    }
    
    @Override
    public void onBackPressed() {
        if (layoutBrowser.getVisibility() == View.VISIBLE) {
            if (!backStack.isEmpty()) {
                goBack();
            } else if (!isViewingShares) {
                showSharesList();
            } else {
                disconnect();
            }
        } else if (layoutShares.getVisibility() == View.VISIBLE) {
            disconnect();
        } else {
            super.onBackPressed();
        }
    }
    
    private static class TransferInfo implements java.io.Serializable {
        String remotePath;
        String localPath;
        long transferredBytes;
        long totalBytes;
        boolean isDownload;
    }
}
