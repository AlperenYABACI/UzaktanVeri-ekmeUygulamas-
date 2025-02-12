import tkinter as tk
from tkinter import messagebox, simpledialog
import subprocess
import os
import datetime
import threading
import time

def run_adb_command(command):
    """ADB komutlarını çalıştırmak için yardımcı fonksiyon."""
    result = subprocess.run(f"adb {command}", shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"ADB komutu başarısız: {result.stderr.strip()}")
    return result.stdout.strip()

def check_usb_device():
    """Bağlı USB cihazları kontrol etmek için ADB komutu."""
    devices_output = run_adb_command("devices")
    devices = [line.split()[0] for line in devices_output.splitlines() if "\tdevice" in line]
    return devices

def get_device_info(device):
    """Cihaz bilgilerini almak için ADB komutları."""
    brand = run_adb_command(f"-s {device} shell getprop ro.product.brand")
    model = run_adb_command(f"-s {device} shell getprop ro.product.model")
    serial = device
    return brand, model, serial

def get_device_ip(device):
    """Cihazın IP adresini almak için ADB komutları."""
    try:
        ip_info = run_adb_command(f"-s {device} shell ifconfig wlan0")
        lines = ip_info.split("\n")
        for line in lines:
            if 'inet ' in line:
                ip_address = line.split()[1]
                return ip_address
        raise Exception("Wi-Fi IP adresi bulunamadı.")
    except Exception as e:
        print(f"Hata: {str(e)}")
        raise

def check_root(device):
    """Cihazın root izinlerini kontrol etmek için ADB komutu."""
    try:
        output = run_adb_command(f"-s {device} shell su -c 'id'")
        return 'uid=0' in output
    except Exception:
        return False

def create_directory(directory):
    """Belirtilen dizini oluşturur."""
    if not os.path.exists(directory):
        os.makedirs(directory)

def pull_files(device, source_directory, destination):
    """Cihazdan belirli bir dizini ve içeriğini çekmek için ADB komutu."""
    pull_command = f"adb -s {device} pull {source_directory} {destination}"
    result = subprocess.run(pull_command, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Çekme hatası: {result.stderr.strip()}")
    else:
        print(f"{source_directory} içeriği başarıyla {destination} dizinine çekildi.")

def pull_disk_image(device, destination_folder):
    """Cihazın disk imajını çekmek için ADB komutu."""
    destination_file = os.path.join(destination_folder, "disk_image.img")
    subprocess.run(f"adb -s {device} shell su -c 'dd if=/dev/block/mmcblk0' | adb -s {device} pull - {destination_file}", shell=True)
    print("Disk imajı başarıyla bilgisayarınıza kaydedildi.")

def create_info_file(destination_folder, brand, model, serial, ip, start_time, is_root):
    """Cihaz bilgilerini içeren bir dosya oluşturur."""
    info_file_path = os.path.join(destination_folder, "cihaz_bilgileri.txt")
    with open(info_file_path, "w", encoding="utf-8") as info_file:
        info_file.write("Cihaz Bilgileri:\n")
        info_file.write(f"Marka: {brand}\n")
        info_file.write(f"Model: {model}\n")
        info_file.write(f"Seri Numarası: {serial}\n")
        info_file.write(f"Root Durumu: {'Rootlu' if is_root else 'Rootsuz'}\n")
        info_file.write(f"IP Adresi: {ip}\n")
        info_file.write(f"Başlangıç Zamanı: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        info_file.write(f"Bitiş Zamanı: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
def connect_device_wifi(device_serial, ip):
    """Cihazı Wi-Fi üzerinden bağlar."""
    try:
        connect_command = f"adb -s {device_serial} connect {ip}:5555"
        result = subprocess.run(connect_command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Wi-Fi bağlantısı kurulamadı: {result.stderr.strip()}")
        print(f"Wi-Fi bağlantısı başarılı: {ip}:5555")
    except Exception as e:
        print(f"Hata: {str(e)}")

def on_device_select():
    """Seçilen cihazla işlem yapmak için butonun tetiklediği fonksiyon."""
    selection = device_listbox.curselection()
    if not selection:
        messagebox.showerror("Hata", "Lütfen bir cihaz seçin.")
        return

    selected_device_info = device_listbox.get(selection[0])
    device_serial = selected_device_info.split(" - ")[2]
    brand, model, serial = get_device_info(device_serial)
    is_root = check_root(device_serial)
    start_time = datetime.datetime.now()

    try:
        ip = get_device_ip(device_serial)
        user_choice = messagebox.askyesno("Bağlantı", f"{brand} - {model} - {serial} cihazı ile {ip} IP adresi üzerinden bağlanılmak üzere. İşlem yapmak ister misiniz?")

        if not user_choice:
            run_adb_command(f"-s {device_serial} disconnect")
            messagebox.showinfo("Bağlantı", "Bağlantı kesildi.")
            return

        # Cihazı Wi-Fi üzerinden bağlama
        connect_device_wifi(device_serial, ip)

        destination_folder = os.path.join("D:/Projeler/AdliBilişimVerileri", f"{brand}_{model}_{serial}_{start_time.strftime('%Y%m%d_%H%M%S')}")
        create_directory(destination_folder)
        create_info_file(destination_folder, brand, model, serial, ip, start_time, is_root)

        messagebox.showinfo("Bilgi", f"{brand} - {model} cihazına Wi-Fi üzerinden bağlanıldı.")

        if is_root:
            action_choice = simpledialog.askstring("İşlem Seçimi", "Cihazdaki evrileri disk imajı ile (fiziksel) mi alalım yoksa klasörler şeklinde(Mantıksal) mi ? (Image/Folder)")
            if action_choice.lower() == "Image":
                pull_disk_image(device_serial, destination_folder)
            elif action_choice.lower() == "Folder":
                adli_data_directories = ["/system", "/data", "/sdcard", "/storage/emulated/0"]
                for directory in adli_data_directories:
                    pull_files(device_serial, directory, destination_folder)
        else:
            adli_data_directories = ["/sdcard", "/storage/emulated/0"]
            for directory in adli_data_directories:
                pull_files(device_serial, directory, destination_folder)

        messagebox.showinfo("Başarılı", "Seçilen işlemler başarıyla tamamlandı ve kaydedildi.")
    except Exception as e:
        messagebox.showerror("Hata", str(e))


def continuously_check_devices():
    """Bağlı cihazları sürekli olarak kontrol eder."""
    known_devices = set()
    while True:
        devices = check_usb_device()
        new_devices = set(devices) - known_devices
        for device in new_devices:
            brand, model, serial = get_device_info(device)
            is_root = check_root(device)
            root_status = "Rootlu" if is_root else "Rootsuz"
            device_info[device] = (brand, model, serial, is_root)
            device_listbox.insert(tk.END, f"{brand} - {model} - {serial} - {root_status}")
        known_devices.update(devices)
        time.sleep(3)

def close_application():
    """Uygulamayı kapatır."""
    root.destroy()

device_info = {}
root = tk.Tk()
root.title("Adli Bilişim Yardım Aracı")

# Pencere boyutunu büyütme
root.geometry("600x400")  # Genişlik x Yükseklik

frame = tk.Frame(root)
frame.pack(pady=20, padx=20)

device_listbox = tk.Listbox(frame, width=80, height=15)
device_listbox.pack(pady=10)

select_button = tk.Button(frame, text="Seçilen Cihazla İşlem Yap", command=on_device_select)
select_button.pack(pady=10)

thread = threading.Thread(target=continuously_check_devices, daemon=True)
thread.start()

root.mainloop()
