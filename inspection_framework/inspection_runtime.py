"""
inspection_runtime.py — 로컬 단독 실행용 런타임
=================================================

[역할]
    InspectionWorker 를 단독 실행(로컬 PC, 터미널)할 때 쓰는 얇은 래퍼입니다.
    OpenCV 창으로 실시간 피드를 보여주고 'q' 키로 종료합니다.

[FastAPI + React UI 와의 관계]
    나중에 FastAPI 서버를 만들면 이 파일 대신
    InspectionWorker 를 직접 사용합니다.
    이 파일은 "카메라에 직접 연결해서 빠르게 확인할 때" 쓰세요.

[흐름]
    run_local(config)
        → InspectionWorker.start()     (백그라운드 스레드 시작)
        → frame_queue 에서 프레임 꺼내 OpenCV 창에 표시
        → 'q' 키 → InspectionWorker.stop()
"""

import cv2
from config import InspectionConfig
from inspection_worker import InspectionWorker


def run_local(config: InspectionConfig, window_scale: float = 0.6):
    """
    단독 실행 함수. 검사 워커를 시작하고 OpenCV 창으로 결과를 보여줍니다.

    Parameters
    ----------
    config       : InspectionConfig 인스턴스
    window_scale : 창 크기 비율 (0.0 ~ 1.0). 기본 0.6.
    """
    worker = InspectionWorker(config)

    try:
        worker.start()
        print(f"[Runtime] '{config.line_name}' 창이 열립니다. 종료하려면 'q' 를 누르세요.\n")

        while True:
            # ── frame_queue 에서 JPEG bytes 꺼내기 ───────────────────
            try:
                jpeg_bytes = worker.frame_queue.get(timeout=0.5)
            except Exception:
                # 프레임 없음 (타임아웃) → 키 입력만 확인
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                # 워커가 오류로 종료됐는지 확인
                if worker.status == "error":
                    print(f"[Runtime] 워커 오류 발생. 종료합니다.")
                    break
                continue

            # ── JPEG → OpenCV 이미지 변환 후 창에 표시 ───────────────
            import numpy as np
            img_array = np.frombuffer(jpeg_bytes, dtype=np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

            if frame is not None:
                h, w = frame.shape[:2]
                display = cv2.resize(frame, (int(w * window_scale), int(h * window_scale)))
                cv2.imshow(config.line_name, display)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        worker.stop()
        worker.join(timeout=5.0)
        cv2.destroyAllWindows()
        print(f"\n[Runtime] 종료 완료. 최종 통계: {worker.stats}")
