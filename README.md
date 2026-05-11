# ⚡ PID & Filtering Tool
### FPV Drone Setup Wizard — FETtec Alpha & Betaflight

A **single-file, offline-capable HTML tool** for setting up and tuning FPV drones.
Works on **PC, Mac, iOS and Android** — no installation, no server, no internet required after download.

> **© 2025 Julian Hillemann — [CC BY-NC-ND 4.0](LICENSE.md)**
> Free to use privately. No selling. No copying without credit. No modifications for redistribution.

---

## 🚀 Quick Start

1. Download [`index.html`](./index.html)
2. Open it in any modern browser (Chrome, Firefox, Safari)
3. Done — no installation needed

**Mobile:** Open the link in Safari (iOS) or Chrome (Android) → Add to Home Screen for an app-like experience.

---

## 🌐 Language / Sprache

The tool supports **German 🇩🇪** and **English 🇬🇧** — toggle with the button in the top right corner.
FPV technical terms (PIDs, TPA, RPM Filter, Feedforward, etc.) remain consistent in both languages.

---

## ✨ Features

### 🔧 Two Firmware Modes
| | FETtec Alpha | Betaflight |
|---|---|---|
| **PIDs** | Alpha scale (P≈1.5, I≈0.02, D≈2.9) | BF scale (P≈45, I≈80, D≈40) |
| **Filter** | Frequency depth + Frame strength | Gyro LPF, D-Term LPF, RPM Filter, Dynamic Notch |
| **Presets** | Standard 5", Racer, Ducted, Sub 250g | Freestyle, Racing, Cinewhoop, Longrange |
| **FC/ESC** | FETtec / GEPRC dropdown | Free text (any hardware) |

### 📐 Physics-Based Calculations
- PID scaling by frame size, KV, cell count, prop geometry
- KV Master Gain analysis with sweetspot detection
- Thrust estimation using `T = CT × ρ × n² × D⁴`
- Setpoint Weight, Frequency Depth, P-Term LPF, Yaw Jump Reduction

### 🎯 Step-by-Step Setup Wizard
10 guided phases from first connection to maiden flight:
Connection · Firmware Flash · ESC & Motor · Receiver & Failsafe · OSD & VTX · PIDs · Filter · Rates · Battery · Pre-Flight

### 🔥 Diagnosis Engine
8 symptom-based troubleshooting guides with calculated fix values:
Hot motors · Oscillations · Wobbling · Drift · Prop-wash · Arm issues · Motor failure · OSD

### 🌀 Prop Selection Guide
Recommendations for all frame sizes (2.5"–10"), 2 vs 3 blade guide, KV compatibility, material guide

### 🧠 KV Physics Education
Loop Gain · KV×Voltage=RPM · Torque vs RPM · PID control range · D-Term noise

### 💾 Profile Management
Save / Export (JSON) / Import · PDF export · 2 default profiles pre-loaded (5" Freestyle, 1750KV @ 6S)

---

## 🛠 Supported Hardware

**FETtec Alpha:** AIO 35A / FC F7 / FC G4 / GEPRC FETtec G4 Alpha Stack + GF50A

**Betaflight:** Any FC/ESC — free text fields, BLHeli32 / AM32 / BLHeli_S, Bidirectional DShot

**Receivers:** ExpressLRS · TBS Crossfire · TBS Tracer · ImmersionRC Ghost · FrSky

**Video:** Analog (SmartAudio/Tramp) · DJI O3 · Caddx Vista · Walksnail Avatar

---

## 📱 Mobile

| Platform | Instructions |
|---|---|
| **iOS** | Safari → Share → Add to Home Screen |
| **Android** | Chrome → Menu → Add to Home Screen |

---

## ⚠️ Disclaimer

All PID and filter values are **calculated starting points**, not guaranteed optimal values.
Always do a props-off test before first flight. Monitor motor temperatures after hover.
**FETtec Alpha PID scale ≠ Betaflight scale** — never transfer values between systems.

---

## 📄 License — CC BY-NC-ND 4.0

**© 2025 Julian Hillemann**

| | |
|---|---|
| ✅ Private use | Allowed |
| ✅ Share freely (with credit) | Allowed |
| ❌ Sell or commercial use | **Prohibited** |
| ❌ Modify and republish | **Prohibited** |
| ❌ Rebrand or copy without credit | **Prohibited** |

Required attribution: `© 2025 Julian Hillemann — PID & Filtering Tool`

Full license text: [LICENSE.md](LICENSE.md) · [creativecommons.org/licenses/by-nc-nd/4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/)

---

*Built for the FPV community. Fly safe. 🚁*
