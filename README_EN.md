# SMB File Manager - User Guide

## Overview

SMB File Manager is a Python-based SMB/CIFS network file management tool for Windows. It features a dual-panel interface with the local file browser on the left and the remote SMB server file browser on the right, supporting drag-and-drop operations for intuitive file transfers.

### Key Features

- **Dual-Panel Interface**: Display both local and remote file systems simultaneously for easy comparison and operation
- **Drag-and-Drop Transfer**: Support drag-and-drop file transfer between local and remote
- **Secure Encryption**: Configuration files are fully encrypted with master password protection
- **Multi-Server Management**: Support saving multiple server connection configurations
- **Real-Time Progress**: File transfer displays progress percentage and transfer speed
- **Tree Navigation**: Tree structure for quick directory browsing

---

## Features

### 1. Connection Management

#### 1.1 First-Time Use
When first launching the program, you need to set a master password (minimum 6 characters). The master password is used to encrypt saved server configuration information.

#### 1.2 Connect to Server
1. Click the "Connect to Server" button in the toolbar
2. Fill in the connection dialog:
   - **Server Address**: IP address or domain name of the SMB server
   - **Port**: Default 445, can be modified according to server configuration
   - **Username**: SMB login username
   - **Password**: SMB login password
   - **Share Name**: Name of the shared folder to access
   - **SMB Version**: Support SMBv1/v2/v3 or auto-negotiate
3. Click "Connect" to establish connection

#### 1.3 Save Configuration
After filling in the information in the connection dialog, click "Save Configuration" and enter a configuration name to save. You can quickly select from the dropdown list next time.

#### 1.4 Disconnect
Click the "Disconnect" button in the toolbar to disconnect from the current server.

### 2. File Browsing

#### 2.1 Local File Browsing
- **Directory Tree**: Local drives and directory tree structure displayed on the left
- **File List**: Files and subdirectories in the current directory shown in the middle-lower area
- **Navigation**: Double-click directory to enter, click address bar to enter path

#### 2.2 Remote File Browsing
- **Server Tree**: Server share list displayed after connection
- **Directory Tree**: Directory structure shown when expanding shares
- **File List**: Remote file list shown in the right-lower area

#### 2.3 Sorting
Click column headers in the file list to sort by that column:
- Name, Size, Modified Time, Type
- Click again to toggle ascending/descending order

### 3. File Transfer

#### 3.1 Drag-and-Drop Upload
1. Select files or directories in the local file list
2. Drag to the remote file list area
3. Files will be uploaded to the current remote directory

#### 3.2 Drag-and-Drop Download
1. Select files or directories in the remote file list
2. Drag to the local file list area
3. Files will be downloaded to the current local directory

#### 3.3 Transfer Progress
- Log area displays transfer progress percentage (updated every 2%)
- Shows real-time transfer speed (B/s, KB/s, MB/s)
- Shows total file count and completed count

### 4. Security Management

#### 4.1 Master Password
- Used to encrypt and protect server configuration
- Must be set on first use
- Default master password: admin (recommended to change)

#### 4.2 Change Master Password
1. Menu: Settings → Change Master Password
2. Enter and confirm new password
3. All configurations will be re-encrypted with the new password

#### 4.3 Reset to Default Password
1. Menu: Settings → Reset to Default Password
2. All saved configurations will be cleared after confirmation
3. Master password reset to default value admin

### 5. Configuration File Encryption

#### 5.1 Encryption Mechanism
- Configuration file `smb_config.dat` is fully encrypted
- Uses Fernet symmetric encryption algorithm
- Key derived from master password via PBKDF2
- Encryption strength: 100,000 iterations

#### 5.2 Security Recommendations
- Set a strong master password (recommended 8+ characters with letters, numbers, and symbols)
- Do not use default master password admin
- Change master password regularly
- Do not save sensitive configurations on public computers

---

## Keyboard Shortcuts

| Action | Method |
|--------|--------|
| Refresh Directory | Press F5 or right-click menu |
| New Folder | Right-click menu → New Folder |
| Delete File | Right-click menu → Delete |
| Rename | Right-click menu → Rename |
| Copy Path | Right-click menu → Copy Path |

---

## System Requirements

- **Operating System**: Windows 10/11
- **Python Version**: Python 3.8+ (for development)
- **Network**: Must be able to access SMB server (port 445 or custom port)
- **Dependencies**:
  - pysmb (SMB protocol support)
  - cryptography (encryption functionality)
  - tkinterdnd2 (drag-and-drop support)
  - Pillow (icon generation)

---

## FAQ

### Q1: Cannot connect to server
- Check if server address and port are correct
- Verify username and password are correct
- Check if firewall allows SMB port
- Try changing SMB version

### Q2: Forgot master password
- Use "Reset to Default Password" feature
- Note: This will clear all saved configurations

### Q3: Slow transfer speed
- Check network connection quality
- Try using SMBv3 protocol
- Reduce number of files transferred simultaneously

### Q4: Where are configuration files
- Configuration file: `smb_config.dat` (encrypted)
- Salt file: `.smb_salt` (key derivation)
- Located in program runtime directory

---

## Version Information

**Current Version**: v1.0

**Changelog**:
- v1.0
  - Full configuration file encryption
  - Dialog centering optimization
  - Transfer progress display optimization
  - Dual connection architecture to solve browsing issues during transfer

---

## Support

For issues, please check error messages in the log area or contact support.

---

*This software is developed using Python + Tkinter, based on the pysmb library for SMB protocol support.*
