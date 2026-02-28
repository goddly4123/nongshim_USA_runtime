"""
example_pinhole.py — 핀홀 검사 라인 실행 예시
================================================

[바이브코딩 가이드]
    이 파일이 커스터마이즈의 시작점입니다!
    아래 "==== 여기를 수정하세요 ====" 구역만 바꾸면
    새로운 라인에 바로 적용할 수 있습니다.

[파일 구조]
    inspection_framework/
    ├── config.py               ← ✅ 모든 설정을 담는 dataclass
    ├── camera.py               ← 카메라 (건드릴 필요 없음)
    ├── detector.py             ← AI 감지 (건드릴 필요 없음)
    ├── rejecter.py             ← 리젝트 신호 (건드릴 필요 없음)
    ├── datamanager.py          ← 데이터 저장 (건드릴 필요 없음)
    ├── inspection_worker.py    ← ✅ 백그라운드 워커 (나중에 FastAPI에서 씀)
    ├── inspection_runtime.py   ← 로컬 단독 실행 래퍼 (건드릴 필요 없음)
    └── example_pinhole.py      ← ✅ 이 파일만 복사해서 수정하세요!

[실행 방법]
    cd inspection_framework
    python example_pinhole.py

[나중에 FastAPI 와 연결할 때]
    이 파일의 InspectionConfig 를 그대로 JSON 으로 직렬화해서
    POST /cameras 에 전송하면 FastAPI 가 워커를 생성합니다.
    (React 관리자 UI가 이 역할을 합니다)
"""

import cv2
from config import InspectionConfig
from inspection_runtime import run_local


# ======================================================================
# ==== 여기를 수정하세요 ====
# ======================================================================

config = InspectionConfig(

    # ── 1) 라인 이름 ──────────────────────────────────────────────────
    # 창 제목 / 저장 파일명 / 로그에 사용됩니다.
    line_name = "4-7-pouch-C",

    # ── 2) 카메라 설정 ────────────────────────────────────────────────
    camera_ip   = "192.168.4.73",               # 카메라 IP
    pfs_file    = "pouch_C.pfs",                # 카메라 설정 파일
    rotation    = cv2.ROTATE_90_CLOCKWISE,      # 회전. 없으면 None.
    crop_region = None,                         # ROI [x1,y1,x2,y2]. 없으면 None.
    # 예: crop_region = [100, 200, 500, 600]

    # ── 3) AI 모델 설정 ───────────────────────────────────────────────
    model_path = "./weights/best.pt",           # YOLOv12 가중치 경로
    device     = "cuda",                        # 'cuda' 또는 'cpu'

    # 클래스별 개별 threshold {"클래스명": 0.0~1.0}
    # - 딕셔너리에 있는 클래스만 불량으로 처리됩니다.
    # - 딕셔너리에 없는 클래스는 박스만 표시되고 리젝트 안 됩니다.
    # - None 으로 설정하면 모든 클래스를 0.5 기준 불량 처리합니다.
    class_thresholds = {
        "defect":  0.70,    # defect 는 70% 이상만 불량
        "pinhole": 0.85,    # pinhole 은 85% 이상만 불량 (오탐 줄이기)
        "scratch": 0.60,    # scratch 는 60% 이상만 불량
    },

    # ── 4) 리젝트 설정 ────────────────────────────────────────────────
    reject_delay_frames = 10,    # 검사 후 몇 프레임 뒤 리젝트?
    time_valve_on       = 0.1,   # 밸브 열림 지속 시간 [초]
    pre_valve_delay      = 0.27,  # 신호 ON 전 추가 대기 [초]

    # ── 5) 데이터 저장 설정 ───────────────────────────────────────────
    save_root   = "/mnt/IMG/4-7/pouch_C",   # 저장 경로
    max_preview = 50,                         # preview 최대 이미지 수
    save_normal = False,                      # 정상 이미지도 저장할지

)

# ======================================================================
# ==== 여기부터는 수정하지 않아도 됩니다 ====
# ======================================================================

if __name__ == "__main__":

    # ── 설정을 JSON 으로 자동 저장 (나중에 React UI 에서 불러옵니다) ──
    config.to_json(f"configs/{config.line_name}.json")

    # ── 로컬 단독 실행 ('q' 키로 종료) ───────────────────────────────
    run_local(config, window_scale=0.6)
