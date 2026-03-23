package org.smbclient.app;

import android.content.Context;
import android.graphics.Color;
import android.graphics.Typeface;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.BaseAdapter;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.util.List;
import java.util.Map;

public class FileListAdapter extends BaseAdapter {

    private Context context;
    private List<Map<String, Object>> fileList;

    public FileListAdapter(Context context, List<Map<String, Object>> fileList) {
        this.context = context;
        this.fileList = fileList;
    }

    @Override
    public int getCount() {
        return fileList.size();
    }

    @Override
    public Object getItem(int position) {
        return fileList.get(position);
    }

    @Override
    public long getItemId(int position) {
        return position;
    }

    @Override
    public View getView(int position, View convertView, ViewGroup parent) {
        LinearLayout layout = new LinearLayout(context);
        layout.setOrientation(LinearLayout.HORIZONTAL);
        layout.setPadding(8, 12, 8, 12);
        layout.setBackgroundColor(Color.WHITE);
        layout.setGravity(Gravity.CENTER_VERTICAL);
        
        Map<String, Object> fileData = fileList.get(position);
        String filename = (String) fileData.get("filename");
        boolean isDir = (Boolean) fileData.get("isDirectory");
        String sizeStr = (String) fileData.get("file_size_str");
        String timeStr = (String) fileData.get("last_write_time_str");

        TextView tvIcon = new TextView(context);
        tvIcon.setTextSize(18);
        tvIcon.setGravity(Gravity.CENTER);
        tvIcon.setPadding(0, 0, 12, 0);
        if (isDir) {
            tvIcon.setText("📁");
        } else {
            tvIcon.setText("📄");
        }
        layout.addView(tvIcon);

        LinearLayout textLayout = new LinearLayout(context);
        textLayout.setOrientation(LinearLayout.VERTICAL);
        textLayout.setLayoutParams(new LinearLayout.LayoutParams(
            0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));

        TextView tvName = new TextView(context);
        tvName.setTextSize(15);
        tvName.setTextColor(Color.parseColor("#333333"));
        tvName.setText(filename);
        if (isDir) {
            tvName.setTypeface(null, Typeface.BOLD);
        }
        textLayout.addView(tvName);

        LinearLayout infoLayout = new LinearLayout(context);
        infoLayout.setOrientation(LinearLayout.HORIZONTAL);
        infoLayout.setPadding(0, 2, 0, 0);
        
        if (!isDir && sizeStr != null && !sizeStr.isEmpty()) {
            TextView tvSize = new TextView(context);
            tvSize.setTextSize(12);
            tvSize.setTextColor(Color.parseColor("#666666"));
            tvSize.setText(sizeStr);
            infoLayout.addView(tvSize);
        }
        
        if (timeStr != null && !timeStr.isEmpty()) {
            if (!isDir && sizeStr != null && !sizeStr.isEmpty()) {
                TextView tvSep = new TextView(context);
                tvSep.setTextSize(12);
                tvSep.setTextColor(Color.parseColor("#999999"));
                tvSep.setText("  |  ");
                infoLayout.addView(tvSep);
            }
            
            TextView tvTime = new TextView(context);
            tvTime.setTextSize(12);
            tvTime.setTextColor(Color.parseColor("#999999"));
            tvTime.setText(timeStr);
            infoLayout.addView(tvTime);
        }
        
        if (infoLayout.getChildCount() > 0) {
            textLayout.addView(infoLayout);
        }

        layout.addView(textLayout);

        if (isDir) {
            TextView tvArrow = new TextView(context);
            tvArrow.setText(">");
            tvArrow.setTextSize(16);
            tvArrow.setTextColor(Color.parseColor("#CCCCCC"));
            tvArrow.setGravity(Gravity.CENTER_VERTICAL);
            tvArrow.setPadding(8, 0, 0, 0);
            layout.addView(tvArrow);
        }

        return layout;
    }
}
