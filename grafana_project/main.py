import math
import random
import time

import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS

# --- NASTAVENÍ PŘIPOJENÍ ---
BUCKET = "my-bucket"
ORG = "my-org"
TOKEN = "my-super-secret-token"
URL = "http://localhost:8086"

# --- Vytvoření klienta ---
client = influxdb_client.InfluxDBClient(url=URL, token=TOKEN, org=ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

# --- Pomocné funkce pro generování dat ---
ecg_wave = (
    [0.0] * 15
    + [0.1, 0.25, 0.1]
    + [0.0] * 5
    + [-0.15, 1.2, -0.4]
    + [0.0] * 5
    + [0.1, 0.35, 0.3, 0.15, 0.0]
    + [0.0] * 50
)


def generate_ecg_point(index):
    return ecg_wave[index % len(ecg_wave)]


def generate_eda_point(index):
    return 5 * math.sin(index * 0.02) + 10 + random.uniform(-0.2, 0.2)


current_temp = 36.6


def generate_temp_point():
    global current_temp
    change = random.uniform(-0.05, 0.05)
    current_temp = max(36.0, min(38.5, current_temp + change))
    return current_temp


def generate_accel_points(index):
    return {
        "x": math.sin(index * 0.1),
        "y": math.cos(index * 0.15) * 0.5,
        "z": -1 + math.sin(index * 0.2) * 0.2,
    }


current_hr = 75


def generate_heart_rate():
    global current_hr
    change = random.uniform(-1, 1)
    current_hr = max(60, min(110, current_hr + change))
    return int(current_hr)


current_resp = 16


def generate_respiration_rate():
    global current_resp
    change = random.uniform(-0.5, 0.5)
    current_resp = max(12, min(25, current_resp + change))
    return int(current_resp)


# --- Hlavní smyčka ---
print("Skript spuštěn, posílám data. Ukončíš pomocí CTRL+C.")
intervals = {
    "semafor": 5.0,
    "ekg": 0.05,
    "eda": 0.2,
    "temp": 3.0,
    "accel": 0.05,
    "vitals": 2.0,
}
last_times = {key: time.time() for key in intervals}
counters = {"ekg": 0, "eda": 0, "accel": 0}

shot_active = False
shot_end_time = 0
shot_flash_state = 1
shot_check_interval = 15.0
last_shot_check_time = time.time()

while True:
    try:
        current_time = time.time()

        # Průstřel alarm
        if (
            not shot_active
            and current_time - last_shot_check_time >= shot_check_interval
        ):
            last_shot_check_time = current_time
            if random.random() < 0.50:  # 15% šance
                print("\n !!! ALARM: PRŮSTŘEL !!!\n")
                shot_active = True
                shot_end_time = current_time + 4
        if shot_active:
            shot_point = (
                influxdb_client.Point("gunshot")
                .tag("pacient", "pacient_01")
                .field("event", shot_flash_state)
            )
            write_api.write(bucket=BUCKET, org=ORG, record=shot_point)
            shot_flash_state = 2 if shot_flash_state == 1 else 1
            if current_time > shot_end_time:
                shot_active = False
                print("\n --- ALARM SKONČIL ---\n")
            time.sleep(0.2)

        # Ostatní data
        if current_time - last_times["vitals"] >= intervals["vitals"]:
            last_times["vitals"] = current_time
            # Odesíláme tepovou a dechovou frekvenci najednou
            hr_value = generate_heart_rate()
            resp_value = generate_respiration_rate()
            vitals_point = (
                influxdb_client.Point("vitals")
                .tag("pacient", "pacient_01")
                .field("heart_rate_bpm", hr_value)
                .field("respiration_rate_brpm", resp_value)
            )
            write_api.write(bucket=BUCKET, org=ORG, record=vitals_point)
            print(f"Tep: {hr_value} BPM, Dech: {resp_value} br/min")

        if current_time - last_times["accel"] >= intervals["accel"]:
            last_times["accel"] = current_time
            counters["accel"] += 1
            accel_values = generate_accel_points(counters["accel"])
            accel_point = (
                influxdb_client.Point("accelerometer")
                .tag("pacient", "pacient_01")
                .field("x_axis", accel_values["x"])
                .field("y_axis", accel_values["y"])
                .field("z_axis", accel_values["z"])
            )
            write_api.write(bucket=BUCKET, org=ORG, record=accel_point)
        if current_time - last_times["ekg"] >= intervals["ekg"]:
            last_times["ekg"] = current_time
            counters["ekg"] += 1
            ekg_point = (
                influxdb_client.Point("ekg_signal")
                .tag("pacient", "pacient_01")
                .field("voltage", generate_ecg_point(counters["ekg"]))
            )
            write_api.write(bucket=BUCKET, org=ORG, record=ekg_point)
        if current_time - last_times["eda"] >= intervals["eda"]:
            last_times["eda"] = current_time
            counters["eda"] += 1
            eda_point = (
                influxdb_client.Point("eda_signal")
                .tag("pacient", "pacient_01")
                .field("conductance", generate_eda_point(counters["eda"]))
            )
            write_api.write(bucket=BUCKET, org=ORG, record=eda_point)
        if current_time - last_times["temp"] >= intervals["temp"]:
            last_times["temp"] = current_time
            temp_value = generate_temp_point()
            temp_point = (
                influxdb_client.Point("temperature")
                .tag("pacient", "pacient_01")
                .field("degrees_celsius", temp_value)
            )
            write_api.write(bucket=BUCKET, org=ORG, record=temp_point)
        if current_time - last_times["semafor"] >= intervals["semafor"]:
            last_times["semafor"] = current_time
            semafor_point = (
                influxdb_client.Point("semafor_stav")
                .tag("zarizeni", "testovaci_semafor_01")
                .field("hodnota", random.randint(1, 7))
            )
            write_api.write(bucket=BUCKET, org=ORG, record=semafor_point)

        time.sleep(0.01)
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"Došlo k chybě: {e}")
        time.sleep(5)
print("\nSkript ukončen.")
