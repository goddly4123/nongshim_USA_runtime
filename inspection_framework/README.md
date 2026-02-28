# AI 비전 검사장치 프레임워크 🔬

> **바이브코딩용** — `example_*.py` 파일만 복사·수정하면 새 라인에 바로 적용됩니다.

---

## 📁 폴더 구조

```
inspection_framework/
├── camera.py               ← Basler 카메라 (pypylon)        [수정 불필요]
├── detector.py             ← YOLOv12 감지 (Ultralytics)     [수정 불필요]
├── rejecter.py             ← 리젝트 신호 큐 관리             [수정 불필요]
├── datamanager.py          ← 이미지·결과 데이터 백업         [수정 불필요]
├── inspection_runtime.py   ← 메인 검사 루프                  [수정 불필요]
└── example_pinhole.py      ← ✅ 이 파일만 복사해서 커스터마이즈!
```

---

## ⚙️ 설치

```bash
pip install ultralytics pypylon-pylon opencv-python
```

---

## 🚀 새 라인 추가하는 방법 (바이브코딩)

1. `example_pinhole.py` 를 복사해 새 이름으로 저장합니다.  
   예: `example_neoguri_ocr.py`

2. 파일 상단의 **"여기를 수정하세요"** 구역만 바꿉니다:

```python
# ── 1) 라인 이름 ──────────────────────────────────
LINE_NAME = "5-10-neoguri"

# ── 2) 카메라 ─────────────────────────────────────
CAMERA_IP   = "192.168.5.10"
PFS_FILE    = "acA1300-60gm.pfs"
ROTATION    = cv2.ROTATE_90_CLOCKWISE
CROP_REGION = [150, 250, 370, 400]   # 날짜 인쇄 영역만 잘라내기

# ── 3) AI 모델 ────────────────────────────────────
MODEL_PATH     = "./weights/neoguri_best.pt"
CONF_THRESHOLD = 0.75
TARGET_CLASSES = ["date_error", "missing_text"]

# ── 4) 리젝트 ─────────────────────────────────────
REJECT_DELAY_FRAMES = 10
TIME_DELAY_SEC      = 0.25

# ── 5) 저장 경로 ──────────────────────────────────
SAVE_ROOT = "/mnt/IMG/5-10/neoguri"
```

3. 실행합니다:
```bash
python example_neoguri_ocr.py
```

---

## 🧩 클래스별 역할 요약

| 클래스 | 파일 | 핵심 메서드 |
|---|---|---|
| `BaslerCamera` | `camera.py` | `open()` `grab()` `set_reject_output()` `close()` |
| `YoloDetector` | `detector.py` | `detect(image)` → `List[DetectionResult]` |
| `Rejecter` | `rejecter.py` | `push(is_defect)` `reset()` |
| `DataManager` | `datamanager.py` | `save_defect()` `save_normal()` `get_preview_paths()` |
| `InspectionRuntime` | `inspection_runtime.py` | `open()` `run()` `close()` |

---

## 💡 주요 커스터마이즈 포인트

### 불량 클래스 지정
```python
# detector.py → target_classes
TARGET_CLASSES = ["defect", "pinhole"]  # 이 클래스만 불량으로 처리
# None 으로 설정하면 YOLO가 감지한 모든 클래스를 불량으로 처리
```

### 리젝트 딜레이 조정
```python
# 컨베이어 속도가 빠를수록 reject_delay_frames 를 줄이세요
REJECT_DELAY_FRAMES = 10   # 10프레임 후 리젝트
TIME_DELAY_SEC      = 0.25 # 에어건 응답 보상 시간
```

### 감지 후 추가 동작 (콜백)
```python
def on_defect(detections):
    # 슬랙 알림, PLC 신호, DB 저장 등 원하는 코드 추가
    send_slack_alert(detections)

runtime = InspectionRuntime(..., on_defect_callback=on_defect)
```

### ROI(관심영역) 설정
```python
# 이미지 전체 대신 특정 영역만 AI에 전달
CROP_REGION = [x1, y1, x2, y2]   # 픽셀 좌표
```

---

## 🖥️ UI 조작 키

| 키 | 동작 |
|---|---|
| `q` | 프로그램 종료 |

---

## 📂 저장 폴더 구조

```
{SAVE_ROOT}/
├── defect/
│   └── 2026-02-24/
│       └── 16/
│           ├── defect-0.93-20260224-160001-line.jpg   ← 원본
│           └── defect-0.93-20260224-160001-line.txt   ← 감지 좌표
├── preview/    ← 최근 불량 이미지 (최대 50개)
├── archive/    ← preview 초과분 자동 이동
└── normal/     ← SAVE_NORMAL=True 시 정상 이미지
```
