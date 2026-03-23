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

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class FileListAdapter extends BaseAdapter {

    private Context context;
    private List<Map<String, Object>> fileList;
    private List<Map<String, Object>> originalList;

    public FileListAdapter(Context context, List<Map<String, Object>> fileList) {
        this.context = context;
        this.fileList = fileList;
        this.originalList = new ArrayList<>();
    }

    public void updateData(List<Map<String, Object>> newData) {
        this.fileList.clear();
        this.fileList.addAll(newData);
        notifyDataSetChanged();
    }

    @Override
    public int getCount() {
        return fileList != null ? fileList.size() : 0;
    }

    @Override
    public Object getItem(int position) {
        return fileList != null && position < fileList.size() ? fileList.get(position) : null;
    }

    @Override
    public long getItemId(int position) {
        return position;
    }

    @Override
    public View getView(int position, View convertView, ViewGroup parent) {
        ViewHolder holder;
        
        if (convertView == null) {
            holder = new ViewHolder();
            
            LinearLayout layout = new LinearLayout(context);
            layout.setOrientation(LinearLayout.HORIZONTAL);
            layout.setPadding(8, 12, 8, 12);
            layout.setBackgroundColor(Color.WHITE);
            layout.setGravity(Gravity.CENTER_VERTICAL);

            TextView tvIcon = new TextView(context);
            tvIcon.setTextSize(18);
            tvIcon.setGravity(Gravity.CENTER);
            tvIcon.setPadding(0, 0, 12, 0);
            layout.addView(tvIcon);
            holder.tvIcon = tvIcon;

            LinearLayout textLayout = new LinearLayout(context);
            textLayout.setOrientation(LinearLayout.VERTICAL);
            textLayout.setLayoutParams(new LinearLayout.LayoutParams(
                0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));

            TextView tvName = new TextView(context);
            tvName.setTextSize(15);
            tvName.setTextColor(Color.parseColor("#333333"));
            textLayout.addView(tvName);
            holder.tvName = tvName;

            LinearLayout infoLayout = new LinearLayout(context);
            infoLayout.setOrientation(LinearLayout.HORIZONTAL);
            infoLayout.setPadding(0, 2, 0, 0);
            
            TextView tvSize = new TextView(context);
            tvSize.setTextSize(12);
            tvSize.setTextColor(Color.parseColor("#666666"));
            infoLayout.addView(tvSize);
            holder.tvSize = tvSize;
            
            TextView tvSep = new TextView(context);
            tvSep.setTextSize(12);
            tvSep.setTextColor(Color.parseColor("#999999"));
            tvSep.setText("  |  ");
            infoLayout.addView(tvSep);
            holder.tvSep = tvSep;
            
            TextView tvTime = new TextView(context);
            tvTime.setTextSize(12);
            tvTime.setTextColor(Color.parseColor("#999999"));
            infoLayout.addView(tvTime);
            holder.tvTime = tvTime;

            textLayout.addView(infoLayout);
            holder.infoLayout = infoLayout;

            layout.addView(textLayout);

            TextView tvArrow = new TextView(context);
            tvArrow.setText(">");
            tvArrow.setTextSize(16);
            tvArrow.setTextColor(Color.parseColor("#CCCCCC"));
            tvArrow.setGravity(Gravity.CENTER_VERTICAL);
            tvArrow.setPadding(8, 0, 0, 0);
            layout.addView(tvArrow);
            holder.tvArrow = tvArrow;

            convertView = layout;
            convertView.setTag(holder);
        } else {
            holder = (ViewHolder) convertView.getTag();
        }

        if (fileList == null || position >= fileList.size()) {
            return convertView;
        }

        Map<String, Object> fileData = fileList.get(position);
        String filename = (String) fileData.get("filename");
        boolean isDir = (Boolean) fileData.get("isDirectory");
        String sizeStr = (String) fileData.get("file_size_str");
        String timeStr = (String) fileData.get("last_write_time_str");

        if (isDir) {
            holder.tvIcon.setText("📁");
            holder.tvName.setTypeface(null, Typeface.BOLD);
            holder.tvArrow.setVisibility(View.VISIBLE);
        } else {
            holder.tvIcon.setText("📄");
            holder.tvName.setTypeface(null, Typeface.NORMAL);
            holder.tvArrow.setVisibility(View.GONE);
        }
        
        holder.tvName.setText(filename != null ? filename : "");
        
        if (!isDir && sizeStr != null && !sizeStr.isEmpty()) {
            holder.tvSize.setVisibility(View.VISIBLE);
            holder.tvSize.setText(sizeStr);
        } else {
            holder.tvSize.setVisibility(View.GONE);
        }
        
        if (timeStr != null && !timeStr.isEmpty()) {
            holder.tvTime.setVisibility(View.VISIBLE);
            holder.tvTime.setText(timeStr);
            if (!isDir && sizeStr != null && !sizeStr.isEmpty()) {
                holder.tvSep.setVisibility(View.VISIBLE);
            } else {
                holder.tvSep.setVisibility(View.GONE);
            }
        } else {
            holder.tvTime.setVisibility(View.GONE);
            holder.tvSep.setVisibility(View.GONE);
        }

        return convertView;
    }
    
    static class ViewHolder {
        TextView tvIcon;
        TextView tvName;
        TextView tvSize;
        TextView tvSep;
        TextView tvTime;
        TextView tvArrow;
        LinearLayout infoLayout;
    }
}
