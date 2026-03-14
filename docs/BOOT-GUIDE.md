# Boot Guide — Ubuntu on USB via toram Method

Install Ubuntu 24.04 LTS onto a 64GB SanDisk USB stick using a Surface Pro 7 (i5, 8GB RAM). The `toram` kernel parameter loads the live ISO into RAM, freeing the USB stick so the installer can write to it.

## What You Need

- Surface Pro 7 (i5, 8GB RAM)
- 64GB SanDisk USB stick (flashed with Ubuntu 24.04 LTS ISO via Rufus — GPT/UEFI)
- USB wireless keyboard with 2.4GHz dongle (the Type Cover does NOT work until linux-surface kernel is installed)
- Multi-port USB adapter (to plug in both the USB stick and the keyboard dongle)

## 1. Disable Secure Boot

Secure Boot must be off or the USB will not boot.

1. Shut down the Surface completely.
2. Hold **Volume Up**, then press and release **Power**. Keep holding Volume Up until the UEFI settings screen appears.
3. Navigate to **Security** > **Secure Boot**.
4. Set Secure Boot to **Disabled**.
5. Save and exit.

## 2. Boot from USB

1. Shut down the Surface.
2. Plug the USB adapter into the Surface's USB-A port. Connect the flashed USB stick and the keyboard dongle to the adapter.
3. Hold **Volume Down**, then press and release **Power**. Keep holding Volume Down until the Surface boots from the USB stick.
4. The GRUB menu should appear.

## 3. Add the toram Kernel Parameter

This loads the entire live filesystem into RAM so you can remove the USB stick during installation.

1. At the GRUB menu, highlight **Try or Install Ubuntu** (do NOT press Enter yet).
2. Press **e** to edit the boot entry.
3. Find the line starting with `linux` — it ends with something like `quiet splash ---`.
4. Add `toram` before `---`, so it reads: `quiet splash toram ---`
5. Press **F10** (or Ctrl+X) to boot with the modified parameters.

## 4. Wait for the Live Environment

Loading the full ISO into RAM takes several minutes on 8GB. The screen may appear to hang — this is normal. Wait until the Ubuntu desktop appears.

With 8GB RAM, approximately 4GB will be used by the loaded ISO, leaving around 4GB free for the installer and system. This is tight but sufficient.

## 5. Connect to WiFi

The Intel AX201 WiFi adapter works with the stock Ubuntu kernel (iwlwifi driver included).

1. Click the network icon in the system tray (top-right).
2. Select your WiFi network and enter the password.
3. Verify connectivity: open a terminal and run `ping -c 3 google.com`.

An internet connection is needed for the installer to download updates and third-party drivers.

## 6. Unmount and Remove the USB Stick

Because the live environment is running entirely from RAM, you can now free the USB stick.

1. Open a terminal.
2. Check what is mounted from the USB:
   ```bash
   mount | grep sd
   ```
3. Unmount any partitions from the USB stick (typically `/dev/sda`):
   ```bash
   sudo umount /dev/sda1
   sudo umount /dev/sda2  # if present
   ```
   If `umount` reports "not mounted", that is fine.
4. Physically remove the USB stick from the adapter.
5. Wait about 10 seconds, then re-insert the USB stick.
6. Confirm the system sees it:
   ```bash
   lsblk
   ```
   You should see the USB stick (e.g., `/dev/sda`) with no mounted partitions.

## 7. Launch the Ubuntu Installer

1. Double-click **Install Ubuntu** on the desktop (or run `ubiquity` from a terminal).
2. Follow the installer prompts: language, keyboard layout, WiFi (should already be connected), updates.
3. When you reach the **Installation type** screen, choose **Something else** (manual partitioning).

## 8. Partition the USB Stick

You need two partitions on the USB stick. **Delete any existing partitions first.**

Identify the USB stick — it will be something like `/dev/sda` (NOT `/dev/nvme0n1`, which is the internal SSD). Check the size to be sure (approximately 58-60 GB for a 64GB stick).

### Create the EFI System Partition

1. Click **+** (or "New Partition Table" first if needed, then **+**).
2. Size: **512 MB**
3. Type: **Primary**
4. Location: **Beginning of this space**
5. Use as: **EFI System Partition**

### Create the Root Partition

1. Select the remaining free space on the USB stick and click **+**.
2. Size: use all remaining space
3. Type: **Primary**
4. Use as: **Ext4 journaling file system**
5. Mount point: **/**

## 9. Set the Bootloader Location

**THIS IS CRITICAL.** If you install the bootloader to the internal drive, you will modify the Surface's Windows boot configuration.

At the bottom of the partitioning screen, find **Device for boot loader installation**. Change it to the USB stick's device — the same drive you just partitioned (e.g., `/dev/sda`), NOT a partition like `/dev/sda1`.

Double-check:
- Boot loader device = `/dev/sda` (the USB stick)
- NOT `/dev/nvme0n1` (the internal SSD)

## 10. Complete the Installation

1. Click **Install Now**. Review the summary and confirm.
2. Set your timezone, username, and password.
3. Wait for the installation to finish. This will take a while on USB.
4. When prompted, click **Restart Now**.
5. Remove the USB stick when prompted (then immediately re-insert it for the next boot).

## 11. First Boot from the Installed USB

1. Shut down the Surface if it did not restart cleanly.
2. Insert the USB stick.
3. Boot from USB using **Volume Down + Power** (same as step 2).
4. Ubuntu should boot from the installed USB stick into your new system.

## 12. Run setup.sh

Once booted into the installed Ubuntu system:

```bash
git clone https://github.com/<your-username>/linux-usb.git
cd linux-usb
chmod +x setup.sh
./setup.sh
```

This will install the linux-surface kernel (enabling the Type Cover keyboard and trackpad), system packages, and LeRobot.

## Troubleshooting

### GRUB menu does not appear
The Surface may be booting from the internal drive. Ensure you are holding Volume Down before pressing Power. If that fails, enter UEFI (Volume Up + Power) and change the boot order to prioritize USB.

### System hangs after adding toram
With 8GB RAM, loading the ISO takes several minutes. Wait at least 5 minutes. If it truly hangs, try without `toram` — but you will need a second USB stick (one for live boot, one as the install target).

### Installer does not see the USB stick
Make sure you unmounted and physically removed/re-inserted the USB stick (step 6). Run `lsblk` in a terminal to verify the device is visible.

### WiFi does not connect
The Intel AX201 should work out of the box. If not, check `dmesg | grep iwlwifi` for firmware errors. You may need to proceed without internet and install drivers after first boot.

### Boots into Windows after install
The bootloader was likely installed to the internal drive. Re-do the install, paying careful attention to step 9. Use Volume Down + Power to select USB boot.
